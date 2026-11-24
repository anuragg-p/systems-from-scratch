# Notes for the lesson writers, and for the agents building modules 06 on

Modules 00 to 05: the engine, the lab and 27 lessons of code, each with its
internal test. Everything here was run on the reference code on an Apple M4
Pro, macOS 26.6.2, Python 3.12.7, numpy 2.4.3 (Apple Accelerate BLAS),
PyTorch 2.10.0 (CPU) and safetensors 0.7.0 (test side only). Not yet run on
Linux (spike 9 of the plan). Times are wall-clock seconds of one run on that
machine, with nothing else running.

## The project

```
engine/__init__.py      02.01   the names: import engine as torch (02.01-04.03 add to it, see track.py NAMES)
engine/nudge.py         01.01   derivative(f, x, h), gradient(f, xs, h): the central difference
engine/value.py         01.02   Value: one float and its gradient, + * ** exp log tanh relu, backward()
                        01.03   Neuron, Layer, MLP on Values
engine/tensors.py       02.01   Tensor over a numpy array: + * ** exp log tanh relu, backward(), tensor(), ...
                        02.02   unbroadcast (in _accumulate)
                        02.03   @ sum mean [] transpose .T reshape/view argmax comparisons float() -=, no_grad
                        02.05   manual_seed, randn, rand (one numpy Generator)
                        04.01   abs var std retain_grad;  04.03 sigmoid
engine/autograd.py      02.02   gradcheck(f, inputs): backward against the nudge
engine/nn/__init__.py   02.04   (file comes with 02.04, holding only `functional`)
                        02.05   Parameter Module Linear ReLU Tanh Sequential
                        04.03   BatchNorm1d, Sigmoid;  04.04 LayerNorm;  05.02 Dropout
                        06.01   Conv2d MaxPool2d Flatten (the last names the engine gains)
engine/nn/functional.py 02.04   relu tanh log_softmax softmax cross_entropy;  05.02 dropout
                        06.01   conv2d max_pool2d (and _windows, _scatter: windows as a view, and back)
engine/nn/init.py       04.02   calculate_gain normal_ uniform_ zeros_ ones_ xavier_* kaiming_*
engine/optim/__init__.py 03.01  Optimizer, SGD;  03.02 momentum (dampening, nesterov);  03.03 Adam;  03.04 AdamW
engine/optim/lr_scheduler.py 03.05  LambdaLR
lab/run.py              00.02   config() (key=value settings), Run (config.json, log.jsonl, summary.json, rng)
lab/stats.py            00.03   mean sd spread welch_t
lab/plot.py             00.03   ticks, lines(): SVG line plots of plain elements, text in currentColor
lab/safetensors.py      02.05   save_file, load_file, read_header (numpy arrays; the library's numpy API)
                        09.03   load_file reads each tensor in place (an @from block inside the 02.05 region)
lab/schedule.py         03.05   warmup_cosine
lab/checks.py           04.06   the five checks
lab/devices.py          06.02   device(torch, name), clock(torch, dev): where a PyTorch run computes, and its time
data/points.py          01.04   two_groups: two moons from a seed
data/fetch.py           03.01   the explicit download, pinned sizes and SHA-256 (whole, no regions)
                        06.03   cifar10: one archive, resumed if dropped, unpacked, every file pinned (@from blocks)
                        09.02   gpt2; fetch_each: separate files, each resumed, or a range of a larger one;  09.04 tinystories
data/mnist.py           03.01   read_idx, load(split, n, standardise)
data/cifar.py           06.03   read_records, load(split, n): CIFAR-10's binary records, standardised per channel
data/__init__.py        03.01   batches(n, size, rng)
data/augment.py         05.03   shift(x, k, rng, fill);  06.03 crop_flip(x, pad, rng)
data/tinyshakespeare.txt 07.01  the text, shipped byte for byte (no regions; FILES_FROM and DATA in track.py)
data/shakespeare.py     07.01   load, chars, encode, decode, split(name): the text as numpy character numbers
data/tinystories.py     09.04   stories, tokenizer, tokens: TinyStories, as 09.01's BPE tokens (kept in the data cache)
models/__init__.py      06.02   (no regions) the networks experiments share, one file each
models/convnet.py       06.02   convnet(torch, width): 3 convolutions and a Linear layer, on either library
models/resnet.py        06.04   Block, ResNet; resnet(n, residual, width), layers(model): He et al.'s CIFAR network
models/ngram.py         07.02   context_codes, lookup, NGram, mixture_weights: count models of any context (numpy)
models/rnn.py           07.03   RNNCell, RNN: the recurrent cell by hand, unrolled in a loop
models/attention.py     07.04   attend(scores, values), Additive: attention, kept apart from its scores
models/seq2seq.py       07.04   Encoder, Decoder, AttentionDecoder, Seq2Seq (forward, generate)
models/gpt.py           08.01   causal_mask, self_attend, SelfAttention (one head: query, key, value, out)
                        08.02   SelfAttention's heads (@from); gelu, MLP, Block, GPT (no positions yet)
                        08.03   Positions; GPT's positions=True (@from): the file modules 09 to 14 start from
models/gpt2.py          09.03   CONFIG, from_gpt2, load: GPT-2 small's published weights in GPT
tokens/__init__.py      09.01   (no regions) text as the numbers a model reads; not "tokenizers" (an installed library)
tokens/bpe.py           09.01   pieces, pairs, merge, train_simple, train, encode, vocab, decode: byte pair encoding
tokens/gpt2.py          09.02   byte_symbols, classes, pattern, split, Tokenizer, load: GPT-2's tokenizer, its own files
experiments/<name>.py   one per lesson (below); loop.py (03.01) and deep.py (04.01) are shared code
                        06.03   images.py: the PyTorch-era loop, tensors(dev, ...), train_epoch, evaluate
                        07.02   sequences.py: bits, contexts, context_bits, sample;  07.03 windows, window_bits
                        08.01   language.py: train, the loop module 08 shares;  08.02 attention_maps, looks
                        08.04   language.py: held_bits (and train's held), save, load;  08.05 top_k, top_p, generate
                        09.01   sequences.py: per_character;  09.03 language.py: loops
experiments/recorded/   06.04   the long run of resnet.py, recorded (DATA in track.py; see "Long runs")
                        07.02   recorded/nplm/: the long run of nplm.py
                        08.04   recorded/gpt/: the long run of gpt.py (no weights: model.safetensors is not shipped)
                        09.04   recorded/tinystories/: the long run of tinystories.py (no weights)
tests/                  NNLL_*.py one per lesson; support.py, helpers for the PyTorch comparisons
                        08.02   support.py: gpt_numpy and its pieces, the GPT again in float64 numpy
                        09.01   support.py: bpe_reference, bpe_replay, unicode_pool, unicode_strings
```

From 06.02 the project needs PyTorch too (`pip install torch`; the CPU build
is enough), and from 06.03 CIFAR-10 (`python3 -m data.fetch cifar10`).
Module 07's text, Tiny Shakespeare, ships with the project: nothing to fetch.
Module 09 fetches GPT-2's files (`python3 -m data.fetch gpt2`, from 09.02) and
TinyStories (`python3 -m data.fetch tinystories`, 09.04).

Run everything from the project's top: `python3 -m experiments.<name>
[key=value ...]`. `./learn run research --at 03.01 -- mnist_lr "lrs=[0.1]"`
does the same in `build/at/research/03.01/`; with nothing after `--`, a
shell there. Quote a setting with brackets: unquoted, zsh reads `[...]` as
a file pattern and stops with `no matches found`. A setting the script does not have is exit status 2 and one line
listing the settings (`curve: no setting 'lrr' (settings: n_train=20, ...)`).
Runs go to `runs/<name>/[<label>/]seed<k>/` (config.json, log.jsonl,
summary.json, and SVG plots in `runs/<name>/`); `out=DIR` moves them.

## Conventions every experiment keeps (keep them in 06 on)

- **The engine line.** A script that trains with tensors has exactly one
  line `import engine as torch` and uses only `torch.`, `nn` and `F` after
  it. Code shared between experiments takes the engine as its first
  argument (`loop.train(torch, model, ...)`, `deep.network(torch, ...)`)
  and imports none; an experiment never imports another experiment (it
  would pull in a second engine). The tests run each such script with that
  line made `import torch` (track.py `on_torch`) and compare.
- **Randomness.** The data, its order, splits, label noise and augmentation
  come from the run's numpy generator (`run.rng`); starting weights and
  dropout masks from the engine's (`torch.manual_seed(seed)`). So on
  PyTorch a script draws different starting weights for the same seed: the
  two engines agree within the spread of seeds, not digit for digit. Where
  a script starts from numpy weights (groups_tensors, the valley in
  momentum) PyTorch gives the same numbers to float32 rounding. Same seed,
  same machine, same engine: the same digits (00.02's test holds it).
- **Every result is several seeds**, printed as `lab.spread`: `0.0542 +-
  0.00668 (min 0.0472, max 0.0645, 5 seeds)`, mean +- sample sd, 3
  significant digits. One seed (`seeds=1`, as a Break it may run) has no
  spread and prints its number alone: `0.897 (1 seed)`. Comparisons print
  Welch's t (infinite with one seed a side: read the numbers instead).
- **Printed numbers that differ between machines or runs**: the times in
  speed and groups_tensors (`... ms`, `... times faster`), and the last
  digits of everything. Paths printed are relative to the project unless
  `out=` was given as an absolute path.
- A run whose loss stops being a finite number stops there and is reported
  as diverged; a plot breaks its line there.
- The engine's float type is float32, as PyTorch's; the PyTorch comparisons
  in the tests are in float64 (`model.double()`).

## Conventions from 06.02 on (PyTorch era)

Every script from 06.02 on, and every module after 06, keeps these, with
the ones above where they still apply (settings, runs, seeds, spread,
Welch's t). The template is experiments/cifar.py (06.03); resnet.py
(06.04) is the same with a long run.

- **`import torch`, not the engine line.** A PyTorch-era script imports
  torch itself (`import torch`, `from torch import nn`, `import
  torch.nn.functional as F`); the learner's code still imports only numpy
  and torch (no torchvision, no DataLoader). Engine-era scripts (00.01 to
  06.01) keep `import engine as torch`, and the tests still run them on
  both (`on_torch`). The engine gains nothing after 06.01. switch.py
  (06.02) is the one script that imports both, by their own names.
- **Device.** Every PyTorch-era experiment has a `device` setting, default
  `"cpu"`: `dev = lab.device(torch, cfg.device)`. `device=auto` takes
  cuda, then mps, then cpu; `cuda` and `mps` name one. Models go there
  with `.to(dev)`, data with `tensors(dev, ...)`. lab imports no engine,
  so lab/devices.py takes torch as its first argument. A page's numbers
  and times are CPU numbers (verify replays them); a page may quote an MPS
  time from these notes, never run one. What MPS does here: 06.02's
  network 12 times PyTorch's CPU step (5.0 against 62 ms), ResNet-20 30
  times (12 against 396 ms a batch of 128), ResNet-56 31 times (37
  against 1158 ms); 06.03's default run only 5 times (8 s against 42 s:
  small batches of a small network spend their time in Python, not on the
  GPU). Worth it for anything past a few minutes.
- **Seeds and determinism.** As before: the data, its order and its
  augmentation from the run's numpy generator (`run.rng`); starting
  weights from `torch.manual_seed(run.seed)` just before the model is
  built (it seeds every device's generator). Same seed, same machine,
  same device: the same digits, byte for byte in log.jsonl and
  summary.json (the 06.02 and 06.03 tests hold it). Measured on the CPU:
  a ResNet-8 trained 10 steps gives the same bytes run after run and with
  1, 4 or 10 threads, so the scripts set no thread count and do not call
  torch.use_deterministic_algorithms. MPS gave the same bytes run after
  run in that test too, but other digits than the CPU (a loss of 2.295255
  against 2.295246 after 10 steps): never compare a GPU's numbers with a
  page's. Across machines the last digits can differ, as before. PyTorch
  uses 10 threads here (the performance cores); 4 were faster for
  ResNet-20 (440 against 320 images a second) with other runs going, but
  that is this machine's, so nothing sets it.
- **Data to tensors.** data/ reads with numpy (data/cifar.py like
  data/mnist.py) and returns numpy arrays; the script turns a whole set
  into one tensor on the device once (experiments/images.py's
  `tensors(dev, x, y)`), an augmented training set once a pass. A batch is
  `x[idx]`, `idx = torch.from_numpy(positions).to(dev)`, the positions from
  `data.batches(n, size, run.rng)`. No copy from numpy per batch.
- **models/.** One file per network family, imported by experiments
  (`from models.resnet import resnet`). models/convnet.py takes the
  library as its first argument (06.02 builds it on both); every later
  model imports torch and subclasses nn.Module (resnet.py: Block, ResNet).
  A model file holds the network only; training lives in experiments.
- **Shared loops.** experiments/images.py (06.03) is the image
  classifiers' loop: `train_epoch(model, opt, x, y, batch, rng,
  scheduler=None)` returns the pass's mean loss and accuracy (the sums stay
  tensors on the device and are read once a pass: `.item()` makes the CPU
  wait for the device), `evaluate(model, x, y)` scores in eval mode
  without a graph and puts the model back in train mode. A module whose
  data is not images writes its own loop file the same way (07 on:
  sequences of tokens). An experiment still never imports another.
- **Timing.** `lab.clock(torch, dev)` is time.perf_counter once the device
  is done (torch.cuda.synchronize, torch.mps.synchronize); a GPU time taken
  without it is the time to queue the work. Times are printed, never
  written to log.jsonl or summary.json (they stay byte-identical). On a
  page every time is a `vary`.
- **Long runs.** A module's one long run (at most 60 minutes on the CPU)
  is the lesson's own script with bigger settings, written with
  `out=experiments/recorded`, so it lands in
  `experiments/recorded/<name>/<label>/seed<k>/` (config.json, log.jsonl,
  summary.json), with its curves (`*.svg`) and what it printed
  (`output.txt`) in `experiments/recorded/<name>/`; all committed, about
  100 KB for 06.04. Log once a pass, not every step, to keep the files
  small. track.py names `experiments/recorded/*` in FILES_FROM (the lesson)
  and DATA (shown as its first lines). Every config.json holds every
  setting, so the command is recovered from it; the test checks the
  recorded run's files and its result, and reruns it only with
  LEARN_RERUN_LONG=1. The script's default run is a short version, under
  60 s, printing the same table.
- **Verify.** verify_tools() cannot name a tool for some lessons only, and
  `needs=` looks for a program on PATH. So track.py's pytorch_era_tools()
  writes empty programs `torch` and `cifar10` into build/tools/research/
  when this python imports torch and when CIFAR-10 is in the cache, and
  names them (their folder goes on verify's PATH). Every session block from
  06.02 on says `needs="torch"`, from 06.03 on `needs="torch cifar10"`:
  on a machine without them the lesson is "missing", not failed, and the
  lessons before 06.02 replay as before. No harness change.

## How the timeline works in a Python track (for whoever writes regions next)

No harness change was needed. The rules this track follows:

- A `@build` region is one whole definition (a `def` or `class`, its
  decorators included), with its comment lines above the code as the
  instructions. Its title is the name it defines: the default stub
  (track.py STUBS) is `def <title>(*args, **kwargs): raise
  NotImplementedError("NN.LL: <title> not written yet")`, so a cut region
  still defines its name. A class that other code subclasses gets
  `# @stub class <name>: pass  # ...` (nn.Module does).
- On the site, a region of a lesson not reached is left out whole (the
  harness folds C definitions, not Python ones), so a region must never be
  the only statement of a body. Put a region's sibling definitions in their
  own regions when anything imports them by name (`from lab.stats import
  mean, sd` broke the build when sd shared mean's region).
- Code outside regions that a later lesson changes is a `# @from NN.LL`
  block with an `# @else` part holding the earlier version (curve.py's
  main(), SGD's signature, the train loop's scheduler). One-line `# @from`
  markers re-export names (engine/__init__.py, lab/__init__.py).
- A feature a later lesson brings is an ordinary Python error before it:
  `TypeError: SGD.__init__() got an unexpected keyword argument 'momentum'`
  at 03.01, `ValueError: a gradient of shape (2, 2) for a tensor of shape
  (2, 1): the inputs of an operation must have the same shape` at 02.01,
  `AttributeError` for a name the engine does not have yet. check-timeline
  holds the engine's names at each lesson to track.py's NAMES table.

## Data

- **Two groups of points** (01.04 on): made by data/points.py from a seed.
  Nothing shipped.
- **MNIST** (03.01 on): not shipped, not downloaded by anything but
  `python3 -m data.fetch mnist`, which puts the four original .gz files
  (11,594,722 bytes) from https://ossci-datasets.s3.amazonaws.com/mnist/
  (the mirror torchvision uses) into `$LEARN_CACHE/mnist/`, default
  `~/.cache/systems-from-scratch/mnist/`, and keeps a file only if its size
  and SHA-256 match the ones pinned in fetch.py (their MD5s match
  torchvision's published ones). Without it, a script stops with exit 1 and
  `mnist is missing: it is not in ... Fetch it once with: python3 -m
  data.fetch mnist`; a test fails with `missing: MNIST is not in ...`, as a
  missing QEMU fails xv6's; check-timeline expects that line instead. The
  site's NOTICE needs a line for the track (nothing redistributed; MNIST's
  terms as the plan records them): not written here, NOTICE is outside the
  track.
- Pixels are standardised with MNIST's own training mean and sd (0.1307,
  0.3081) unless `standardise=False` (03.03 and 03.04 use the paper's 0..1
  scale). `load` caches per process: never change its arrays in place.
- **CIFAR-10** (06.03 on): the binary version, from the dataset's own page,
  https://www.cs.toronto.edu/~kriz/cifar-10-binary.tar.gz (which now
  redirects to cave.cs.toronto.edu; urllib follows it), fetched only by
  `python3 -m data.fetch cifar10` into `$LEARN_CACHE/cifar10/`. The archive
  is 170,052,171 bytes, SHA-256 c4a38c50...a1dd pinned in fetch.py; its MD5
  is c32a1d4ab5d03f1284b67883e8d87530, the one the page publishes. Seven
  files are taken out of it (tarfile, by name, no extractall) and kept only
  if each matches its pinned size and SHA-256: data_batch_1..5.bin and
  test_batch.bin (30,730,000 bytes each: 10,000 records of a label byte and
  3072 pixel bytes, red then green then blue, row by row) and
  batches.meta.txt (61 bytes, the class names); the archive is deleted.
  The server is slow and drops connections: my first download died at 117
  MB after 30 minutes, so fetch_archive resumes a partial `.part` with an
  HTTP Range request, up to five times (tested: a cut archive finished its
  last 1 MB through the redirect in 15 s). Missing, a script stops with
  exit 1 and `cifar10 is missing: it is not in ... Fetch it once with:
  python3 -m data.fetch cifar10`; a test fails with `missing: CIFAR-10 is
  not in ...`; check-timeline expects the line (track.py DATASET_OF names
  the experiments that need it). Its page states no licence and asks that
  the tech report be cited (Krizhevsky 2009); NOTICE has the line.
- CIFAR-10's images are standardised per channel with the training set's
  own mean (0.4914, 0.4822, 0.4465) and sd (0.2470, 0.2435, 0.2616) on the
  0..1 scale (measured over all 50,000; data/cifar.py's MEAN and STD).
  `load(split, n)` reads only as many files as n needs and caches per
  process, as mnist.load does.
- **Tiny Shakespeare** (07.01 on): shipped, `data/tinyshakespeare.txt`,
  byte for byte the file karpathy/char-rnn has at
  `data/tinyshakespeare/input.txt` (fetched 2026-11-24 from
  raw.githubusercontent.com at master, commit 6f9487a6fe5b...; the file is
  unchanged since the repository's first commit, 370cbcd4, 2015). 1,115,394
  bytes, 40,000 lines, SHA-256
  86c4e6aa9db7c042ec79f339dcb96d42b0075e16b8fc2e86bf0ca57e2dc565ed, MD5
  6fb458f1232090904fb40fe944165e91. Plain ASCII (no byte above 127, no
  carriage return), so `./learn check`'s ASCII rule holds and one byte is
  one character. 65 characters: newline, space, ! $ & ' , - . : ; ?, the
  digit 3, A-Z, a-z (`$` occurs once, `&` three times, `3` 27 times, all in
  the training part). The plays are public domain; char-rnn's Readme gives
  MIT; NOTICE has the entry. The test pins size and hash. track.py puts it
  in FILES_FROM (07.01) and DATA (the site shows its first 20 lines).
- The split is by position, never shuffled (data/shakespeare.py SPLITS):
  train = the first 90% (characters 0 to 1,003,853), validation the next
  5% (55,770 characters, from 1,003,854), test the last 5% (55,770, from
  1,059,624; it starts mid-word, "rance ta'en"). Validation is The Taming
  of the Shrew; test is its end and then The Tempest, a play whose names
  (Prospero, Miranda, Ariel) never occur in training: every model scores
  about 0.2 bits per character worse on test than on validation (4-character
  add-k 2.42 against 2.63, deleted interpolation up to 5 2.23 against 2.42).
  So settings are chosen on validation and every reported score is on
  test; never compare a validation number with a test number.
- `split(name)` encodes with a dict per character (about 0.1 s for the
  whole text) and caches per process, as mnist.load does: never change its
  arrays in place. Scripts make a split one tensor on the device once
  (`torch.from_numpy(a).to(dev)`), as 06.03's tensors() does for images.

- **GPT-2 small** (09.02 on): not shipped; `python3 -m data.fetch gpt2`
  puts vocab.json (1,042,301 bytes, SHA-256 196139668b...6783),
  merges.txt (456,318, 1ce1664773...adc5) and model.safetensors
  (548,105,171, 248dfc3911...a707) into `$LEARN_CACHE/gpt2/` from
  https://huggingface.co/openai-community/gpt2/resolve/607a30d783dfa663caf39e06633721c8d4cfcd7e/
  (fetched 2026-11-24, 73 s; data/fetch.py has the full hashes). Each was
  checked before it was pinned: the model's SHA-256 is the X-Linked-ETag
  the site sends for that LFS file (NOTES on 08 found it); vocab.json and
  merges.txt are plain git files there (their ETags are git blob SHA-1s,
  which match), and their SHA-256s are exactly the ones tiktoken pins for
  OpenAI's own encoder.json and vocab.bpe at
  openaipublic.blob.core.windows.net/gpt-2/encodings/main/: byte for byte
  OpenAI's files. Licence as read at the source on 2026-11-24: the
  Hugging Face model card's metadata says `license: mit` (that repository
  has no licence file); OpenAI's own repository, github.com/openai/gpt-2,
  has a "Modified MIT License" (Copyright (c) 2019 OpenAI: MIT, plus "We
  only ask that you use GPT-2 responsibly and clearly indicate your
  content was created using GPT-2", and the notice need not go with
  content the model makes). Nothing of it is in the project; NOTICE has
  the entry. A dropped connection
  carries on (fetch_each, an HTTP Range request; tried: a vocab.json cut at
  500,000 bytes finished through the site's redirect, byte for byte).
  Missing, a script stops with exit 1 and `gpt2 is missing: ... Fetch it
  once with: python3 -m data.fetch gpt2`; a test runs the checks that need
  no download, then fails with `missing: GPT-2 ... is not in ...` and the
  command, as 06.03 does without CIFAR-10 (see Tests).
- **TinyStories** (09.04): not shipped; `python3 -m data.fetch tinystories`
  puts train.txt (67,108,864 bytes: bytes 0 to 67,108,863 of
  TinyStories-train.txt, one Range request; SHA-256 1aa3e816...8d82,
  computed here) and valid.txt (TinyStories-valid.txt whole, 19,447,282
  bytes, SHA-256 94e43181...38b4, equal to the site's X-Linked-ETag) into
  `$LEARN_CACHE/tinystories/`, from
  https://huggingface.co/datasets/roneneldan/TinyStories/resolve/f54c09fd23315a6f9c86f9dc80f725de7d8f9c64/
  (fetched 2026-11-24, 11 s). TinyStories-train.txt is the file the
  paper's models were trained on (the dataset card: "The models referred
  to in the paper were trained on TinyStories-train.txt"); it is
  1,924,281,556 bytes, stories by GPT-3.5 and GPT-4, each followed by a
  line `<|endoftext|>`. The first 64 MiB hold 74,394 whole stories (the
  range ends mid-story: dropped); valid.txt 21,990. The repository also has
  TinyStoriesV2-GPT4-train.txt (2.2 GB, GPT-4 only, "of higher quality"
  per the card), not used: the paper's file was. Licence as read on the
  card on 2026-11-24: CDLA-Sharing-1.0 (its metadata; the card states no
  other terms); NOTICE has the entry. data/tinystories.py keeps what it
  makes in the same folder: bpe4096.json, train-bpe4096.npy,
  valid-bpe4096.npy (see 09.04).

## The lessons: code, default run, time, and what held

Times: the default run, `python3 -m experiments.<name>`, wall clock.

| lesson | experiment | seconds |
|---|---|---|
| 00.01-00.03 | curve | 0.3 |
| 01.01 | nudge | 0.3 |
| 01.02 | graph | 0.3 |
| 01.03 | network | 0.3 |
| 01.04 | two_groups | 15.4 |
| 02.01 | speed | 0.9 |
| 02.02 | broadcast | 0.3 |
| 02.03 | groups_tensors | 0.7 |
| 02.04 | softmax | 0.3 |
| 02.05 | checkpoint | 0.4 |
| 03.01 | mnist_lr | 2.1 |
| 03.02 | momentum | 1.7 |
| 03.03 | adam | 33.0 |
| 03.04 | adamw | 25.3 |
| 03.05 | schedule | 17.4 |
| 04.01 | deep_stats | 3.9 |
| 04.02 | init | 7.8 |
| 04.03 | batchnorm | 27.6 |
| 04.04 | layernorm | 26.2 |
| 04.05 | residual | 28.5 |
| 04.06 | bugs | 11.7 |
| 05.01 | random_labels | 10.9 |
| 05.02 | regularise | 29.9 |
| 05.03 | augment | 20.8 |
| 05.04 | double_descent | 5.8 |
| 06.01 | conv (engine) | 27.0 |
| 06.02 | switch | 4.1 |
| 06.03 | cifar | 43.4 |
| 06.04 | resnet (short; the long run, 40 minutes: see 06.04) | 53.5 |
| 07.01 | bigram (numpy only) | 0.3 |
| 07.02 | nplm (short; the long run, 20 minutes: see 07.02) | 38.6 |
| 07.03 | rnn | 46.4 |
| 07.04 | attention | 37.0 |
| 08.01 | self_attention | 15.2 |
| 08.02 | heads | 46.8 |
| 08.03 | positions | 38.9 |
| 08.04 | gpt (short; the long run, 56 minutes: see 08.04) | 35.1 |
| 08.05 | sampling (no checkpoint: trains its own small GPT; with 08.04's long-run checkpoint 85 s) | 36.9 |
| 09.01 | bpe | 37.8 |
| 09.02 | tokenizer (needs GPT-2's files) | 8.4 |
| 09.03 | gpt2 (needs GPT-2's files) | 44.4 |
| 09.04 | tinystories (short; the long run, 45 minutes: see 09.04; with its checkpoint 45 s) | 24.1 |

06.01 to 06.04 were timed twice, the second time with other agents' runs
going (load average 6 to 8): conv 26.4 and 27.0, switch 3.7 and 4.1, cifar
42.1 and 43.4, resnet about 50 and 53.5. Same digits both times.

07.01 to 07.04 were timed twice in a row with the defaults (10 threads),
the machine never quite quiet: a virtual machine took 1 to 7 cores all
afternoon and Spotlight one, load average 3.8 to 5.6 during the runs:
bigram 0.33 and 0.32, nplm 38.6 and 37.5, rnn 46.4 and 44.9, attention 37.0
and 36.3; the same digits both times, and the same as a third run before
them. With other agents' runs going as well (load 7 to 14) the same
settings took up to 1.5 times as long (rnn 57 to 73 s at 800 steps), the
10 threads spending as much time in the system as in the work: so the
defaults were cut to these (07.02's network 2500 to 2000 steps, 07.03's 800
to 600, 07.04's 1200 to 1000; their entries give both sets of numbers).
On a machine with nothing else running they should be faster still.

08.01 to 08.05 were timed twice in a row with the defaults (10 threads),
the machine never quiet: a virtual machine took 4 to 5 cores the whole
time, load average 4.6 to 7.6 during the runs: self_attention 15.2 and
15.1, heads 46.8 and 44.8, positions 38.9 and 38.9, gpt 35.1 and 33.0,
sampling 35.0 and 36.9; the same output both times. Earlier, with other
agents' runs going as well (load 10 to 18), the same settings took two to
three times as long (heads 101 s, positions 88, sampling 72 to 110), the
10 threads spending nearly as much time in the system as in the work;
with OMP_NUM_THREADS=1 at load 5 to 8 heads took 45 s and positions 39:
these small models gain nothing from threads. heads is the module's
slowest default.

Spike 1 (engine speed): one MNIST epoch (784-100-10, batches of 128, SGD)
takes 0.14 s on the engine, 0.23 s on PyTorch; 0.41 s against 0.38 s with
512 hidden units. The engine is not the bottleneck anywhere in 00 to 05.

**00.01 One experiment, end to end.** experiments/curve.py at 00.01 is one
file, numpy only, no lab: a cubic fitted to 20 noisy points of sin(pi x)
(noise sd 0.2) by 2000 steps of gradient descent, lr 0.5, gradient
`2 X.T (X w - y) / n` by hand. Seed 0: train 0.0104, test 0.0496 (the noise
floor is 0.04).

**00.02 The same run twice.** curve.py's main() moves onto lab.config and
lab.Run (@from blocks). Two runs, same seed: identical log.jsonl and
summary.json bytes (the test compares them). config.json holds every
setting, the label and the seed.

**00.03 Five seeds.** curve over 5 seeds: test loss `0.0542 +- 0.00668 (min
0.0472, max 0.0645, 5 seeds)`: one run's test loss can be 0.047 or 0.065 by
the seed alone, a 37% swing. Plots `runs/curve/train_loss.svg`. Over 50
seeds (`seeds=50`) it is `0.0576 +- 0.0132 (min 0.0408, max 0.124, 50
seeds)`: twice the sd five seeds show, and a worst seed (30, its training
points stopping short of both ends) nearly twice theirs. Five seeds can
miss the tail, so the three-seed comparisons of modules 03 to 05 may
understate their spread too: treat a t near 3 there as suggestive.

**01.01 A derivative by nudging.** f(x) = x^3 - 2x at 1.5 (4.75 exactly):
central error 1.0e-2 at h = 0.1, falling as h^2 to 1.3e-10 at h = 1e-5,
then rising (4.5e-10 at 1e-6, 3.9e-7 at 1e-9, 2.7e-3 at 1e-13); one-sided
error falls only as h (4.6e-1 at 0.1). Best central h: 1e-5. Plot
`runs/nudge/error.svg` (both on log axes: the V).

**01.02 A graph of Values.** One neuron tanh(x1 w1 + x2 w2 + b) with
x1 = 1.5, x2 = -0.5, w1 = 0.8, w2 = -1.2, b = -1 (our numbers, not
micrograd's): o = 0.6640; d o/d n = 0.5591; backward and nudge agree to
1.2e-10. backward() is iterative (a 5000-node chain is fine).

**01.03 A neuron, a layer, a network.** MLP(2, [4, 4, 1]): 37 weights;
12 to 26 of them get exactly no gradient at one point (their relu is off).
Backward against nudge: 3e-11 to 1e-10. Weights uniform in [-1, 1] from
`random.Random(seed)`.

**01.04 Training it.** MLP(2, [8, 8, 1]) on 50 points of two moons, hinge
loss, full-batch descent lr 0.5, 80 steps, 3 seeds: loss 1.16 -> 0.012,
0.88 -> 0.040, 1.18 -> 0.061; training accuracy `0.987 +- 0.0115`; on 200
fresh points `0.975 +- 0.015`. 15 s: the scalar engine is slow, which is
02.01's point. (At lr 0.2 and 60 steps it reached only 0.947 and 0.892.)
With no hidden layer (`"sizes=[1]"`): training accuracy `0.9 +- 0.02` at 80
steps and still at 800, fresh points `0.868 +- 0.0503`: the 1986 paper's
claim, that hidden units learn what a network without them cannot, held at
this size (the page says what it does not test).

**02.01 The scalar engine is a thousand times too slow.** speed: tanh(x y +
x) and its gradients for 20,000 pairs: scalar Values 158 to 190 ms, one
tensor 0.12 to 0.18 ms: 916 to 1674 times faster across our runs with
nothing else running, down to 795 with another run going (timing: vary);
gradients equal to 1.3e-15. Sums do not exist yet at 02.01 (they are
02.03's), so the experiment uses `out.backward(torch.ones_like(out))`.

**02.02 Broadcasting.** broadcast: five pairs of shapes, each gradient in
its own input's shape, gradcheck ok for all; a bias of 4 added to 5 rows
gets gradient [5, 5, 5, 5]. Identical output on PyTorch (the test compares
stdout). gradcheck checks a random weighting of the outputs (one backward
per input), not the full Jacobian PyTorch's builds: say so if the page
compares them.

**02.03 Matrix multiply, sums and indexing.** groups_tensors: the two
groups with the network as matrices (2-16-16-1), 200 points, 1000 steps, 3
seeds: training accuracy 1.0, fresh points `0.998 +- 0.0015`, 0.14 to 0.16
ms a step across our runs (01.04's scalar step on 50 points: 60 to 70 ms). Starting weights come
from numpy, so PyTorch gives the same numbers.

**02.04 Softmax and cross-entropy.** softmax: scores [100, 99, 0] and
[1000, 999, 0] give nan from the definition, [0.7311, 0.2689, 0.0000] from
F.softmax; cross-entropy of [0, 50, -50] for class 0 is 65.0000, finite;
equal scores over 10 classes lose 2.3026 = log(10). Identical stdout on
PyTorch. The engine silences numpy's overflow warnings, as PyTorch has none.

**02.05 Modules and a checkpoint.** checkpoint: 2-16-16-2 trained with
cross-entropy by hand-written SGD (optimisers are 03), saved, header
printed (`0.weight {'dtype': 'F32', 'shape': [16, 2], 'data_offsets': [64,
192]}` ...; 1848 bytes, header 424), loaded into a new network: the same
scores, number for number. The format lives in lab/safetensors.py, not in
the engine: it takes numpy arrays, so either engine writes the same file
(state_dict -> `.numpy()`). The test reads ours with the safetensors
library, ours reads the library's, and a checkpoint PyTorch trained loads
into the engine with the same scores.

**03.01 MNIST, and a rate that is too big.** mnist_lr: 784-100-10, one
pass, batches of 128, SGD, 3 seeds. Last-50-step loss / test accuracy:
lr 0.01 `0.428` / `0.894`; 0.1 `0.205` / `0.946`; 0.5 `0.156` / `0.954`;
2.0 `2.16` / `0.212`. At 2.0 it does not go to nan: within 3 steps the
batch loss jumps to about 194 (2.36, 3.36, 49.3, 194.4), the jump kills
most hidden units, and the loss sits near log(10). Two measures of the
units left, both right (seed 0): units that fire for at least one digit of
the step's own batch of 128 go 100 -> 95 -> 64 -> 40 -> ... -> 1 by step
100 (3 at the end); units that fire for at least one of the 10,000 test
digits, the lesson's measure (`dead_units` is 100 minus it), go 100 -> 98
-> 71 -> 52 -> ... -> 14 by step 100 and 12 at the end (6 to 12 over the
three seeds; 23 still fire for some training digit). A unit silent on one
batch can still fire for rarer digits, so the batch count is the lower;
quote the lesson's. The log has every step (every=1) so the jump shows on
the curve.

**03.02 Momentum.** momentum: valley (w0^2 + 50 w1^2)/2 from (-4, 1), lr
0.03: plain descent needs 186 steps to a loss below 1e-4, momentum 0.8
needs 52 (0.9 needs 84: it overshoots); paths in `runs/momentum/valley.svg`.
MNIST, one pass: plain lr 0.05 `0.269`, momentum 0.9 at 0.05 `0.130`,
plain at its best rate 0.5 `0.156`. No randomness in the valley: PyTorch
takes the same number of steps.

**03.03 Adam (paper: Kingma and Ba, section 2.1, figures 1 and 2).** Changed
from the plan's claim, which did not hold beyond noise: the race is a tie at
this size, so the lesson's failure-then-fix is part 1, the property the paper
states in section 2.1 (the step is invariant to rescaling of the gradient).
1. The valley of 03.02, (w0^2 + s w1^2) / 2 from (-4, 1), in float64, steps
   to a loss below 1e-4 (at most 5000): momentum 0.8 at lr 0.03, 0.01,
   0.003, 0.001 takes 52, 84, 354, 1108 at s = 50 and diverges at s = 5000;
   at 0.0003 it takes 3742 at both. Adam at lr 0.1: 109 at s = 50, 111 at
   s = 5000. First step at s = 5000: momentum (0.0003) moves w0 by 0.0012
   and w1 by 1.5, Adam (0.1) each by 0.1 (with the bias correction m_hat /
   sqrt(v_hat) = g / |g| at step 1). The loss times 1000, s = 50: momentum at
   0.03 diverges, at 3e-05 takes the same 52 steps; Adam at 0.1 the same 109
   steps, every weight within 7.8e-9 of its path on the loss itself (eps is
   the whole difference). PyTorch prints part 1 digit for digit (the test
   compares it). Part 1 adds under half a second; `"models=[]"` runs it alone.
2. The race: pixels on the paper's 0..1 scale, batches of 128, 3 passes,
   each optimiser at the best rate of a grid (Adam 3e-4, 1e-3, 3e-3; SGD
   with Nesterov momentum 0.9 at 0.01, 0.03, 0.1), 3 seeds, the cost on the
   whole training set after each pass. Logistic regression: after pass 1
   Nesterov is lower (0.2968 against 0.3091, t = -11.8), after passes 2 and
   3 Adam is lower within noise (t = +1.8, +1.2): about the same, which is
   what the paper's figure 1 says for this model. Network 784-256-256-10
   (the paper's has 1000 units and dropout): Adam lower after pass 1
   (0.0966 against 0.1060, t = +1.3) and 2 (t = +0.6), Nesterov lower after
   pass 3 (0.0444 against 0.0510, t = -1.3): none of it beyond noise. So
   "Adam's cost falls fastest on the multilayer network" did not show at
   this size; say that. With standardised inputs (`standardise=True`) tuned
   Nesterov ends clearly lower (spike: 0.0403 against 0.0497 after 3
   passes, 2 seeds). Adam is the less seed-stable one here (sd 0.0085
   against 0.0019). These numbers are unchanged by part 1.

**03.04 AdamW (paper: Loshchilov and Hutter).** Changed: three parts.
1. SGD: an L2 term and weight decay give the same step (difference 2.8e-17);
   Adam with L2 against AdamW: 2.0e-3 apart after one step, where the decay
   itself is at most 1.8e-6. (The decay must shrink the weight before the
   step, at the weight the gradient was taken at; the first version shrank
   it after and the two differed by 8e-6.)
2. 67 of 784 pixels are 0 in every training image (pixels 0..1), so their
   weights get no gradient from the data. Logistic regression, one pass,
   lr 1e-3: Adam with L2 drives them to 0.0% of their size at wd 1e-4 and
   at wd 1e-2 alike (Adam normalises wd * w to a step of about lr), while
   the busy weights grow to 423% and 283%; AdamW leaves them at 99.5%
   (wd 0.01) and 62.5% (wd 1), exactly (1 - lr wd)^469. Same on PyTorch.
3. The paper's figure 2 at laptop size (2000 images, 40 passes, MLP 256, 2
   seeds, test error %): Adam + L2 best 7.58 (lr 3e-3, wd 1e-3), AdamW best
   7.59 (lr 3e-3, wd 0.3); 2 of 12 settings within 0.3 points of the best
   for each. The paper's "wider good region" did not show; say so.
   PyTorch's AdamW multiplies the decay by lr, so its wd and lr are coupled
   again, unlike the paper's lambda.

**03.05 Schedules (Loshchilov and Hutter's cosine; warmup as practice).**
schedule: 784-256-256-10, Adam, 2 passes, 3 seeds. Worst batch loss in the
first 300 steps / training cost / test error %: constant 1e-3: 2.298 /
`0.0659` / `2.77`; constant 3e-3: 2.298 / `0.0683` / `2.98`; cosine from
3e-3: 2.298 / `0.0382` / `2.02`; cosine from 1e-2: 3.459 / `0.0546` /
`2.60`; cosine from 1e-2 with 200 warmup steps: 2.298 / `0.0453` / `2.34`.
Both claims hold: decay to 0 at a higher peak beats the best constant rate,
and a warmup takes the early spike away (2.298 is the starting loss: with
the warmup the loss never goes above where it began).

**04.01 Twenty layers that learn nothing.** deep_stats: 20 linear layers,
64 wide, nn.Linear's own start (uniform +-1/sqrt(fan_in), variance 1/(3
fan_in)), so each relu layer shrinks the variance by 6 (spread x0.41 a
layer; measured x0.41 from layer 1 to 19). Spread over the batch: layer 1 0.257, layer
10 5.3e-5, layer 19 3.3e-8; gradient arriving at layer 1 5.3e-11. One pass
of SGD (lr 0.01, momentum 0.9), 3 seeds: loss `2.301 +- 0.0006`, log(10) =
2.3026. Tanh the same (gradient at layer 1 2.5e-8, nothing saturated: it
is the shrinking, not saturation). PyTorch's own default start does the
same (the test runs it): the "obvious thing" here is PyTorch's default.

**04.02 Initialisation (He et al., figure 3).** init: 30 layers, 64 wide,
relu, one pass, 3 seeds. nn.Linear's start: `2.3` (nothing); Glorot: `2.25
+- 0.084 (min 2.15)`: stalls, one seed moves a little; He: `0.805 +- 0.153`.
Spread at layer 29: 1.8e-8, 1.7e-5, 0.285. The paper's 30-layer claim holds.
At 20 layers (`init depth=20 "inits=['glorot','he']"`) Glorot trains, slowly
and unevenly: `0.886 +- 0.381 (min 0.598, max 1.32)` against He's `0.298 +-
0.00491`. (An earlier spike's "0.60 to 0.74" did not reproduce.)

**04.03 Batch normalisation (Ioffe and Szegedy).** batchnorm, two parts.
1. Their figure 1(a) at laptop size: 3 hidden layers of 100 sigmoid units,
   batches of 60, SGD lr 0.5, nn.Linear's start, 3 seeds. Test accuracy at
   250 / 500 / 1000 / 3000 steps: without 0.286 / 0.803 / 0.916 / 0.959,
   with 0.891 / 0.908 / 0.930 / 0.961; 90% at step 1000 against 500. Holds,
   early; they meet by 3000.
2. 20 relu layers, He's start, one pass, SGD momentum 0.9: at lr 0.1
   without batch norm 2.301, nan, 1.790 (stuck, diverged, bad); with it
   0.382, 0.384, 0.429. At lr 0.01 though, batch norm is worse (0.438
   against 0.305): it lets the rate go up, it does not make this network
   train faster at a rate that already works. Do not stretch part 1 into a
   claim about part 2.

**04.04 Layer normalisation (Ba, Kiros and Hinton).** layernorm: one digit
with two different sets of batchmates: batch norm's output differs by
3.464, layer norm's by 0.000; batch of one: batch norm raises PyTorch's
message (`Expected more than 1 value per channel when training, got input
size (1, 4)`; PyTorch's says `torch.Size([1, 4])`), layer norm is fine;
batch of two: batch norm makes every feature +-1 (-0.993, +1.000, ...).
Training the sigmoid network for 3000 steps, 3 seeds: batches of 2, lr
0.02: batch norm `0.531`, layer norm `0.843`; batches of 60, lr 0.5: batch
norm `0.961`, layer norm `0.944`. Batch norm wins at 60, loses badly at 2.

**04.05 Residual connections (He et al., figures 1 and 4).** residual:
plain (linear, batch norm, relu) against residual blocks of two layers
(relu(x + bn(linear(relu(bn(linear(x))))))), 8 and 32 layers, 64 wide,
He's start, one pass, SGD lr 0.01 momentum 0.9, 3 seeds. Training cost:
plain 8 `0.167`, plain 32 `1.05`; residual 8 `0.137`, residual 32 `0.147`.
The plain half of the claim holds (degradation, t = +53). The residual half
did not: 32 layers train about as well as 8 but not better (t = +3.4, the
deeper slightly worse after one pass); say "about as well", not "better".
The gradient reaching layer 1 at the start: plain 32 is 0.90 against plain
8's 0.011 (with batch norm in a deep plain stack the gradient explodes, it
does not vanish), residual 32 0.068.

**04.06 Five bugs that do not crash.** bugs: 784-128-BN-128-BN-10, Adam
1e-3. The five checks of lab/checks.py on the correct script and five
broken copies, 3 seeds: the correct one passes all; each bug fails exactly
its own check in 3 of 3 seeds and no other. What each check saw: no
zero_grad: the second backward's gradient is 2.00 times the first's;
softmax before cross_entropy: one batch only gets from 2.306 to 1.462 (the
floor is log(e + 9) - 1 = 1.461); labels shuffled apart from the images:
held-out accuracy 0.108; pixels 0-255: starting loss 12.8 against log(10)
2.303; scored without model.eval(): 2376 of 5000 predictions change with
the order (batches sorted by digit). Same table on PyTorch.

**05.01 Random labels (Zhang et al., figure 1a).** random_labels: 1000
training digits, 512-512, Adam 1e-3, 60 epochs, 3 seeds; validation =
the last 10,000 of MNIST's training set, test = the test set, scored once.
Real labels: every training label right at epoch 10 (all seeds), validation
`0.902`, test `0.894`. Random labels: every label right at epoch 40 to 45,
validation `0.102`, test `0.104` (chance 0.1). On PyTorch one seed reached
100% at epoch 40 and drifted back to 98.2% by epoch 60 (Adam): the claim is
the epoch it got there, which the test checks.

**05.02 Weight decay and dropout (Srivastava et al., table 2).**
regularise: 2000 digits, 512-512, AdamW 1e-3, 50 passes, 3 seeds, test
error %: neither 8.11, weight decay (0.5) 7.74 (t = -4.4), dropout (0.2 on
the pixels, 0.5 after each hidden layer, as the paper places it) 6.93
(t = -10.7), both 7.09. On validation neither (7.4) and weight decay (7.14)
come in the same order, but dropout and both swap and tie within noise:
both 6.47 +- 0.139, dropout 6.49 +- 0.232. The paper's MNIST
numbers are for 60,000 images (1.60% to 1.25%); ours are not a
reproduction of those.

**05.03 Augmentation.** augment: the same network and data, each pass every
image shifted by a new random whole number of pixels (pad with blank, crop
at an offset): none 8.14, up to 1 pixel 5.17, up to 2 pixels 4.76 (t =
-26.5); training error rises from 0.00 to 0.85.

**05.04 Double descent (Nakkiran et al.).** Changed: the plan's spike 2
asked for a sweep of network widths under 30 minutes; at laptop size the
run is the random-features model of Belkin et al. (2019), which the paper
cites: p random relu features of the image (a first layer fixed at random),
a second layer fitted exactly by least squares with the smallest weights
(np.linalg.lstsq; gradient descent from zero reaches the same weights, the
test checks it on a small case), 1000 training digits, 10% of labels
random, 3 seeds. Test error: p = 200 27.0% (the first minimum), 800 48.7%,
950 71.5%, 1000 88.3% (test mse 1285: the peak, at p = n), 1050 71.6%, 2000
30.3%, 10000 17.4%, below the first minimum. Holds, strongly. It is not a
network trained by gradient descent on the page; say so. Five seconds.
The paper sees double descent "most strongly in settings with label
noise"; here the peak does not need it: with `noise=0` it is 86.8% against
88.3%, and only the error either side of it falls (p = 200 24.2%, 10000
12.0%). The docstring and 05.04 say so.

**06.01 Convolution: the same weights at every position.** The engine gains
F.conv2d(input, weight, bias=None, stride=1, padding=0), F.max_pool2d(input,
kernel_size, stride=None, padding=0), nn.Conv2d(in_channels, out_channels,
kernel_size, stride=1, padding=0, bias=True) (starting as Linear does,
uniform +-1/sqrt(in_channels kh kw), which is PyTorch's default),
nn.MaxPool2d and nn.Flatten(start_dim=1, end_dim=-1); stride, padding and
kernel_size take a number or a pair. Every window is a view
(np.lib.stride_tricks.sliding_window_view, `_windows`), the windows become
the rows of one matrix (the copy numpy makes) and one `@` with the filters
is the convolution; the way back is the matrix product's (02.03), then
`_scatter` adds each window's gradient back onto the pixels it read, one
strided add per place in the kernel. Values and gradients equal PyTorch's
at 1e-6 in float64 for every stride and padding tried (the test), gradcheck
clean. Max pooling sends the gradient to the first of equal largest
numbers, as PyTorch's CPU kernel does. No avg_pool2d: it was written and
dropped, nothing uses it (06.04's ResNet averages with `x.mean((2, 3))` on
PyTorch). One pass over 10,000 digits with the experiment's network takes
about 1.4 s on the engine.
conv, three parts, 10,000 training digits, 2 passes of SGD (lr 0.05,
momentum 0.9, batches of 64), 3 seeds, test on 5,000 digits:
1. Moved k pixels (a quarter of the test digits up, down, left, right;
   blank comes in): fully connected 784-100-10 (79,510 weights) k = 0..4:
   `0.911`, `0.851`, `0.638`, `0.404`, `0.234`; convolutional (two 3 by 3
   convolutions of 8 and 16 filters, each with relu and 2 by 2 max
   pooling, then Linear 784 to 10: 9,098 weights) `0.949`, `0.926`,
   `0.825`, `0.640`, `0.427`; t = +5.3 at k = 0, +16.8 at k = 2, +20.6 at
   k = 4. Held: the network with a ninth of the weights is better
   unmoved and loses less. Did not hold, and is the lesson's honest second
   half: it is far from shift-proof. At 4 pixels it keeps 0.43.
2. Why: test digit 0 (a 7) moved 4 pixels up through the trained network,
   seed 0: after the first convolution, rows 1-22 of the moved digit's
   maps equal rows 5-26 of the unmoved one's, largest difference 0
   (exactly); after the second pooling the 7 by 7 maps, rows 1-4 equal
   rows 2-5, again 0. The features are all there, moved one cell; the
   Linear layer has a weight per place and reads another digit: scores
   move by up to 15, the prediction goes from 7 to 2. So: convolution
   is equivariant (exactly), the network is not invariant. Two 2 by 2
   poolings turn a move of 4 pixels into a move of exactly one cell, and
   other moves into other maps; neither is ignored. Spike, not in the default
   run: replacing the Linear head with an average over every position
   (global average pooling, conv 16-32-32) makes the network far more
   tolerant (0.91 at k = 0, 0.74 to 0.75 at k = 4) but it needs 3 passes
   and 10 s a run to get there, too slow for the minute; after 1 or 2
   passes it is still at 0.68 to 0.89 unmoved.
3. Pixels shuffled by one permutation (each run draws its own from
   run.rng, the same for its training and test digits): fully connected
   `0.898` (t = -1.2 against unshuffled: no difference beyond noise; the
   shuffled run is a different draw of batch order, so its digits are not
   the unshuffled run's), convolutional `0.821` (t = -8.9). Still well
   above chance: the Linear head can learn from any arrangement, the
   convolutions' locality no longer helps.
26 s on the engine; on PyTorch (the line changed) 19 s and the same table
within the spread (fc 0.914 .. 0.236, conv 0.945 .. 0.412, shuffled 0.902
and 0.829). The two "largest difference 0" lines came out exact on both
here; the test checks the engine's only.
The page (lessons agent) also quotes LeCun et al. 1998, section II and
II.A, read at the source: fully connected nets "have no built-in invariance
with respect to translations", "shift invariance is automatically obtained
by forcing the replication of weight configurations across space", the
shifted feature map, and "The input variables can be presented in any
(fixed) order without affecting the outcome of the training" (part 3 tests
it). Its Break it makes `_scatter` assign (`=`) instead of add (`+=`): a
4 by 4 image's gradient under a 2 by 2 filter of ones goes from the window
counts (1, 2, 4) to all 1, gradcheck raises, and conv seeds=1 still gets
0.956 on unmoved digits (seed 0 with the right gradient: 0.958): the wrong
gradient reaches only the first convolution's weights, and SGD trains with it.

**06.02 One import: the same script on PyTorch.** Changed from the plan's
failure. The plan said the engine is too slow for what comes next; on this
machine's CPU that is not much of a failure: the engine's convolution is
numpy's matrix product (Apple Accelerate), and PyTorch's macOS arm64 build
has no oneDNN (torch.backends.mkldnn.is_available() is False), so its CPU
convolution, the backward above all, is a slow path. Measured, a training
step of models/convnet.py (width 32, batches of 128): engine 116 and 119
ms in two runs, PyTorch on the CPU 62 and 54 ms (1.9 and 2.2 times),
PyTorch on the Apple GPU 5.0 ms (23 times the engine). ResNet-20's 19
convolutions without batch norm (a scratch script, not in the project):
engine 728 ms, PyTorch CPU 359 ms, MPS 10 ms. The lesson's case for the
switch is
therefore: (1) the GPU, 12 to 36 times PyTorch's own CPU on these networks
and only from PyTorch; (2) what the next lessons need that the engine does
not have (BatchNorm2d for ResNet, then embeddings, attention, mixed
precision, published weights), each another engine lesson. A CPU build
with oneDNN (Linux x86) may make PyTorch's CPU convolution much faster
than here: not measured (spike 9), so do not claim it. Say "about twice
as fast on this laptop's CPU", never "a thousand times".
switch, default (cpu): part 1, float64, one SGD-with-momentum step on 128
random images, 3 seeds: the loss differs by 1.3e-16, every gradient by at
most 4.7e-17, every weight after the step by at most 2.4e-17 (relative):
the same arithmetic in another order. Part 2, float32, the same start and
the same 11 batches: the losses agree to 7 digits for 4 steps and drift to
1.8e-5 by step 10 (rounding in another order, growing through the steps;
the loss does not fall: random labels). Times (vary): engine 116 ms,
PyTorch 62 ms, a pass over 50,000 images 45 s against 24 s; in the second
run 119 and 54 ms, 46 and 21 s. 3.7 s.
device=auto adds a column for mps: its losses match the engine's to 7
digits for longer than the CPU's do; 5 ms a step, 2 s a pass.
06.01's conv.py with `import torch` instead of the engine line: 19 s
against 26 s, the same table within the spread (06.01 above): that is the
"one import" demonstration for the page.
lab/devices.py: `device(torch, name)`, `clock(torch, dev)`; models/convnet.py:
`convnet(torch, width=32)`, 113,738 weights at 32, 33,834 at 16 (06.03's).
Changed for the page (lessons agent): switch.py now also calls
`torch.manual_seed(seed)` (part 1) and `torch.manual_seed(0)` (part 2) before
building PyTorch's network, whose weights copy_weights then replaces, so its
output is unchanged. Without it PyTorch's default generator is seeded anew in
every process (torch.initial_seed() differs run to run), and 06.02's Break it,
which comments out the copy, printed other numbers every run; seeded, it prints
the same (loss 9.6e-03 apart, weights up to 0.32). The page's run with
`device=auto`, with other runs going (load 4 to 8): engine 138 ms, PyTorch CPU
75.7 ms, mps 7.1 ms a step; the mps losses equal the engine's to the 7 decimals
printed until step 8 (2.3242767 against 2.3242760), the CPU's until step 4.

**06.03 A convolutional network on CIFAR-10.** cifar: the first 2000
training images, 12 passes, batches of 64, SGD momentum 0.9, 3 seeds, test
on 2000 test images; fully connected 3072-256-10 (789,258 weights) at lr
0.01, convolutional (models/convnet.py, width 16: 33,834 weights) at lr
0.02. In the sweep the fully connected network got 0.38 to 0.40 at 0.01,
0.33 to 0.35 at 0.02 and 0.16 to 0.31 at 0.04 and 0.05; the convolutional
one about the same at 0.01 and 0.02 (0.509 and 0.515 at 4000 images x 10
passes, 0.473 and 0.462 at 2000 x 16), but with crops and flips 0.01 left
it undertrained (2000 x 16: 0.470 against 0.497), so 0.02 for both of its
rows. Training / test
accuracy / gap: fully connected `0.962` / `0.380` / 0.582; convolutional
`0.799` / `0.455` / 0.344; with crops and flips (pad 4, random 32 by 32
window, mirrored half the time, new every pass) `0.564` / `0.486` / 0.078.
t = +8.1 (convolutional against fully connected), +3.0 (crops and flips
against without). 42 s on the CPU, 8 s on mps (the same table within the
spread).
Held: the convolutional network with 1/23 of the weights is better on test
images, and memorises far less. Crops and flips: the gap closes from 0.34
to 0.08, the test accuracy rises 3 points. How much they buy depends on
the length of training: in the sweep, at 3000 images and 10 passes they
did not raise test accuracy at all (t = -2.1, lr 0.02, on mps), at 2000
and 16 passes by 3.5 points (t = +4.5), at 1000 and 30 passes by 6
(t = +2.5). Augmentation pays when the network would otherwise memorise;
say "here, 3 points", not "always". No paper's claim is run here (the
dataset's report and LeNet are reading); He et al.'s numbers come in 06.04.
The page (lessons agent) runs the 3000 x 10 case on the CPU (`cifar
n_train=3000 epochs=10`, 62 s with other runs going): conv `0.501`, crops and
flips `0.49`, t = -1.9, gaps 0.253 and 0.059: no gain, as on mps. Its Break
it flips rows instead of columns in crop_flip (upside down): crops and flips
`0.392` on test, training 0.456, t = -3.2 against none. A real fetch into an
empty cache took 2418 s (40 minutes) with no dropped connection.

**06.04 ResNet (He et al. 2015, section 4.2, figure 6 and table 6).**
models/resnet.py is the paper's CIFAR-10 network: a 3 by 3 convolution of
16 filters, three stages of n blocks (16, 32, 64 filters on 32, 16, 8
pixels; the first convolution of stages 2 and 3 steps 2), global average
pooling (`x.mean((2, 3))`), Linear to 10; batch norm after every
convolution (convolutions without bias), He's normal start (fan_in, 04.02).
6n + 2 layers with weights; 75,290 / 269,722 / 464,154 / 658,586 /
853,018 / 1,727,962 weights for 8 / 20 / 32 / 44 / 56 / 110 layers, the
paper's 0.27M, 0.46M, 0.66M, 0.85M and 1.7M (table 6). The shortcut is
option A, the one the paper uses on CIFAR-10: the identity, and where a
block halves the map and doubles the filters, every second pixel of every
second row (`x[:, :, ::2, ::2]`) with zero channels appended (`F.pad(x,
(0, 0, 0, 0, 0, extra))`; the paper does not say where the zeros go, we
put them after). So plain and residual have exactly the same weights,
names and count. The paper's training: SGD momentum 0.9, weight decay
1e-4, batches of 128, lr 0.1 divided by 10 at 32k and 48k of 64k steps,
crops and flips on 45k/5k train/validation, per-pixel mean subtracted.
Ours: the same but the rate (see below), the steps (the schedule's drops
at half and three quarters of ours), the data (the first n_train training
images; per-channel standardisation, 06.03) and no validation split (the
claim is about training error).
The claim, in the paper's terms (section 4.2, figure 6 left and middle,
and figure 1): the deeper plain network has the higher training error;
with shortcuts the deeper network is not worse, and in the paper better.

The long run, recorded in experiments/recorded/resnet/ (config.json,
log.jsonl and summary.json of every network and seed; plain.svg and
residual.svg, training error dashed and test error solid per pass, as the
paper's figure 6 draws them; output.txt, what it printed):

    python3 -m experiments.resnet "depths=[20,56]" width=16 n_train=4000 n_test=1000 epochs=8 batch=128 lr=0.01 seeds=3 out=experiments/recorded

4000 training images, 8 passes (256 steps), 3 seeds, test on 1000.
Training error % at the end (scored after training, in eval mode, on the
4000 images without crops): plain 20 `71.9 +- 1.51` (70.3, 73.3, 72.1),
plain 56 `81.8 +- 2.96` (78.4, 83.5, 83.5), t = +5.2: every seed of the
deeper plain network ends above every seed of the shallower. Residual 20
`59.2 +- 0.694`, residual 56 `55.0 +- 1.88` (53.7, 54.1, 57.1), t = -3.7:
the deeper one is better, as in the paper. Test error: plain 73.4 and
81.6, residual 61.0 and 57.5. Both halves of the claim held, in the
paper's own pair of depths (its figure 1) and width, on 4000 images.
The curves: the plain networks separate from the first pass (training
error after it 86.5 against 89.0 on average) and stay apart; the residual
56 is below the residual 20 from pass 1 on (82.3 against 83.0, then 65.0
against 66.7 at pass 4). 39.7 minutes of training, 39 min 45 s wall clock
in all, on the CPU (10 threads, about 2.2 cores busy: PyTorch's CPU
convolution backward is mostly one thread here), with other agents'
runs going (load average 5 to 10); a run alone should be a little
faster. On mps the same settings took 1.5 minutes (spike, below).

Short (default) run, resnet: 800 training images, 3 passes, batches
of 64, lr 0.01, 2 seeds, 8 and 20 layers (the 56-layer network is too slow
for a minute of CPU: 1.14 s a step of 128): plain 8 `78.5 +- 3.89`, plain
20 `85.7 +- 0.795` (t = +2.6); residual 8 `78.4 +- 1.77`, residual 20 `75.8
+- 3.27` (t = -1.0); test 82.1, 87.4, 78.8, 78.4. 53 s with other runs
going (0.9 minutes of training). The same kind of table and the same
direction, but 39 steps is barely training: the residual half is within
noise there, the long run is the evidence. Two seeds only, for time; say
so. The test checks the plain half (+2) and that residual 20 is far below
plain 20 (-4), not the residual half.
The page's Break it (lessons agent) comments out `out = out + shortcut` in
Block.forward: the residual rows of the short run then equal the plain rows
digit for digit (78.5 and 85.7, t = +2.6, test 82.1 and 87.4), since the two
networks are built in the same order from the same seed and see the same
images. The module's cover (art/outlines/research_art.py) now prints the
long run's four training errors and asserts them (71.9, 81.8, 59.2, 55.0).

What the lesson must not say: that this reproduces the paper's figure
(our networks are a few hundred steps into training; the paper's errors
are a few percent); that 0.1 "fails" (it is too large for these deep
networks at the start of training, which the paper itself says of its
110-layer one); that 20 against 56 shows the same at every rate (at 0.02
the residual networks are level, at 0.1 the deeper one is far behind).
Our number beside the paper's: the paper's table 6 test error is 8.75%
for ResNet-20 and 6.97% for ResNet-56 (6.61 +- 0.16 for 110 over five
runs); the paper gives the plain networks only as curves (figure 6 left:
plain-56 above plain-20; figure 1 the same pair). Ours, in the long run:
training error 59.2 and 55.0 (residual 20 and 56), 71.9 and 81.8
(plain); test error 61.0 and 57.5, 73.4 and 81.6. The direction holds;
the size is nowhere near.

Spike 3 (which depths, width, images and passes show plain against
residual in under 60 minutes of CPU). Explored on the Apple GPU (about 30
times the CPU here; the same seeds give other last digits but the same
behaviour), then run on the CPU. Training error % at the end, plain
shallow/deep (t), residual shallow/deep (t); 2 seeds unless said.
- [8, 20], 2000 images x 4 passes, lr 0.1: 66.7/70.7 (+2.7), 64.5/61.2
  (-1.9). 5000 x 10: 46.4/56.0 (+5.1), 47.9/45.8 (-1.0). 10000 x 10:
  35.6/43.7 (+2.9), 37.2/34.5 (-2.2). Both halves, but 8 layers is not one
  of the paper's networks.
- [20, 56] at the paper's lr 0.1: 5000 x 9, 1 seed: 59.7/76.6 and
  49.7/77.4: the deeper residual network is as bad as the deeper plain
  one. Without crops and flips the same (52.0/75.2, 37.0/71.3). Batches of
  64 (twice the steps): 52.9/83.7 (+8.2), 48.5/80.2. 10000 x 15, 1 seed:
  37.7/70.4, 26.8/46.3. Its log shows why: the first pass ends at a loss
  above log(10), then the network sits near 2.27 (training error 85 to 90%)
  for several passes, the "slightly too large to start converging" the
  paper reports for 110 layers. At this length 56 layers behave like the
  paper's 110.
- [14, 32] lr 0.1, 5000 x 10: 50.1/63.7 (+11.4), 45.2/57.1 (+5.9).
  [20, 32] lr 0.1, 7500 x 10: 48.3/59.0 (+3.6), 38.2/44.8 (+5.5). The
  plain half holds everywhere; the residual half fails at 0.1.
- The paper's remedy for 110 layers (0.01 until the training error is
  below 80%, about 400 steps, then 0.1): as a fixed 400 steps it came to
  0.01 for most of these short runs ([20, 32] 7500 x 10: 52.2/59.0 (+9.6),
  42.7/40.6 (-3.0)); going back to 0.1 after it broke the deep residual
  network again ([20, 56] 10000 x 15, 1 seed: 37.6/78.6). Dropped: a
  lower rate throughout is simpler and is what worked.
- The rate, [20, 32], 6000 x 10: 0.01: 65.4/70.5 (+3.3), 51.5/48.6
  (-3.9); 0.02: 57.0/62.7 (+3.2), 44.5/44.0 (-2.9); 0.05: 47.7/57.7
  (+4.9), 40.2/40.5 (+1.2). [20, 56], 5000 x 9: 0.01: 68.2/81.7 (+4.5),
  55.0/51.0 (-16.0); 0.02: 60.5/80.2 (+2.8), 48.8/49.4 (+0.7); 0.05:
  55.5/76.2 (+13.1), 47.0/66.0 (+2.8, the two seeds 59.2 and 72.9).
- Chosen: the paper's figure-1 pair, 20 and 56 layers, width 16 (the
  paper's), lr 0.01, 4000 images, 8 passes, batches of 128, 3 seeds. On
  the GPU first: 71.1/85.8 (+10.3), 59.4/55.4 (-6.9); with 10 passes
  68.5/85.0 (+11.9), 56.6/52.8 (-10.5). Cost on the CPU: ResNet-20 about
  320 images a second, ResNet-56 about 110 (10 threads; a step of 128 is
  0.40 s and 1.14 s), so 4000 x 8 x 3 seeds was estimated at 50 minutes
  (it took 40); 5000 x 9 would be over the hour.
- Width 8 saves less than half on the CPU (ResNet-20 0.24 s a step
  against 0.40 s; ResNet-56 0.68 against 1.14) and the short run at width
  8 showed neither half (82.0 against 84.2, t = -0.7); width stays 16.

**07.01 Counting pairs (Shannon 1951).** bigram, numpy only (no torch, no
device setting: counting needs neither), one Run (seed 0, which only the
sample uses; every other number is exact, the same on every run). The
training text has 1,003,853 pairs, 1380 of the 65 x 65 = 4225 possible.
1. The pair model, k = 0, on the first 12 characters of the test text,
   each line count of the pair, count of the first, p, -log2 p: 'ra' 2375
   / 44271 = 0.0536, 4.220 bits; ... "a'" 58 / 49718 = 0.0012, 9.743. Mean
   4.282 bits; 2 ** 4.282 = 19.45, the perplexity. Over all 55,769 test
   pairs: inf, because 176 of them (12 distinct: '-D' 'DR' 'EB' 'FE' 'IB'
   'NZ' 'O\n' 'SP' 'Sy' 'dt' 'fn' 'rz') never occur in training: p = 0.
2. Every count plus k, on validation: k = 0 inf, 1 3.5696, 0.1 3.5678,
   0.01 3.5682, 0.001 3.5688; chosen 0.1. With a million characters the
   pair table is full enough that k hardly matters (0.002 bits); in 07.02
   it matters a great deal.
3. The ladder on the test text (perplexity): equal chances 6.022 (65.0) =
   log2 65; single characters 4.850 (28.8); pairs 3.599 (12.1). On the
   training text with k = 0 (the counts' own text): 6.022, 4.774 (27.4),
   3.537 (11.6).
4. Shannon's table (BSTJ 30, 1951, page 54), 27 letters: F0 4.76, F1 4.03,
   F2 3.32 (F3 3.1, Fword 2.14; 26 letters 4.70, 4.14, 3.56, 3.3, 2.62),
   computed from published tables of letter, pair and triple frequencies
   (Pratt 1942): each F_N is an entropy of the text the frequencies came
   from, not a score on held-out text, so ours beside his are the training
   column. The training text folded to his 27 symbols (letters made small,
   everything else a space, runs of spaces one): 4.75, 4.09, 3.32. With all
   65 characters: 6.02, 4.77, 3.54. Say the text and the alphabet differ;
   the folded F2 matching his to 3 digits is a coincidence of two texts,
   not a reproduction. His prediction experiments (with 100 letters known,
   "of the order of one bit per letter") are not run here.
5. 300 characters from the pair model, k = 0.1, seed 0, starting after a
   newline ("NE ETornetl / V: / Whan ashe:'thend se! ...").
0.3 to 0.5 s. For the theory rule, every number a page derives is printed: the
p of a pair as count / count, -log2 p, the mean, 2 to the mean, log2 65.
Trailing spaces are stripped from printed sample lines (the summary keeps
the text exact).
Changed for the page (lessons agent): the second line printed reads "...;
of the 65 x 65 = 4225 possible pairs, 1380 occur" (it ran the two clauses
together). The page derives the grouping of the mean by pair (the mean over
positions of -log2 p equals Shannon's -sum p(i, j) log2 p_i(j): 3.537 both
ways on the training text, a fact on the page) and 02.04's cross-entropy of
equal scores over 65 classes, 4.174 nats = 6.022 bits. Its Break it writes
pair_counts as `table[ids[:-1], ids[1:]] += 1` (numpy adds once per distinct
pair): the table holds 1,380 in all, every cell 0 or 1, k = 0.001 is chosen
(validation 4.9568), pairs score 4.988 on test, worse than single characters
(4.850), the folded F2 is 4.53. Validation 3.5678 against test 3.599 for
pairs at k = 0.1. VINCENTIO (Measure for Measure's duke) speaks 193 times in
the training text, not at all in validation.

**07.02 Longer contexts, and Bengio et al. (2003).** nplm. Counting with
contexts of 0 to 7 characters (models/ngram.py): contexts seen 1, 65,
1,380, 11,228, 48,539, 133,293, 264,623, 413,620 of 65^n possible (65^5 =
1.16e9); the (context, next) pairs seen are 100%, 33%, 4.1%, 0.27%,
0.012%, 3.5e-4%, ... of those possible; the test text's contexts never
seen in training 0, 0, 0.3, 2.2, 5.5, 11.7, 22.8, 37.3%. Training bits
(k = 0, Shannon's F_{n+1} of this text) fall 4.774, 3.537, 2.746, 2.151,
1.754, 1.419, 1.097, 0.804; test bits with add-k (k from 1, 0.3, ...,
0.001 chosen on validation: 0.001 for singles, 0.1 for pairs, 0.03 from
2 on) 4.850, 3.599, 3.044, 2.659, 2.629, 2.979, 3.515, 4.109: best at 4,
then up. Deleted interpolation (the paper's own baseline: every order up
to n mixed, one weight per order fit by EM on validation; an order's
chance after a context never seen is 1 / V): up to 1 3.612, 2 3.033, 3
2.632, 4 2.445, 5 2.416, 6 2.410, 7 2.409; the weights at 5 are 0.001
0.013 0.080 0.254 0.365 0.288. Up to 1 it is worse than add-k (3.612
against 3.599): weights fit on validation (The Shrew) and scored on test
(The Tempest).
The network (NPLM: embeddings of 24, 512 tanh units, Adam 0.01 falling to
0 along a cosine, 2000 steps of 1024 random positions, 3 seeds; no direct
connections, no dropout by default), test bits, against add-k and
interpolation of the same context, and mixed half and half with
interpolation (the paper's "mix"):
- context 1: 3.594 +- 0.0011 / 3.599 / 3.612 / 3.592: the pair model
  again; "lower" than both by 0.005 and 0.018, nothing to make of it.
- context 3: 2.606 +- 0.0074 / 2.659 / 2.632 / 2.553: lower than both.
- context 5: 2.474 +- 0.0070 / 2.979 / 2.416 / 2.330: far below add-k,
  0.058 above interpolation in every seed: in a minute it has not caught
  up with the paper's baseline. Mixed, 0.09 below it.
(At 2500 steps, the first default: 3.593, 2.601, 2.466, mixed 2.329; it
took 46 to 69 s with 10 threads and the machine busy, so 2000.)
Nearest by embedding (context 5, seed 0; among the 53 characters seen
1000 times or more; random vectors of 24 numbers have cosine spread 0.20):
'.' -> '?' 0.75, '!' 0.72; '!' -> '.' 0.72, '?' 0.69; 'a' -> 'A' 0.32;
's' -> 'S' 0.35; 'e' -> nothing above 0.22. Only sentence-ending
punctuation is clearly grouped; capitals with their small letters
weakly; the rest is within the noise of the random start. Say that.
Sample from context 5, seed 0 ("Third his kiss selffeconce me hand, / And
gels exerelow, with than here hear off stery soul. ...").
The long run, recorded in experiments/recorded/nplm/ (every config.json,
log.jsonl and summary.json, training.svg: each network's batch bits every
100 steps, output.txt; seed 0 of context 8 keeps its 65 x 32 embeddings
in its summary.json for a figure):

    python3 -m experiments.nplm "contexts=[1,3,5,8]" embed=32 hidden=1024 dropout=0.3 steps=20000 lr=0.003 seeds=3 out=experiments/recorded

19 min 59 s of wall clock (1198 s by its own clock; user 1867 s) with
OMP_NUM_THREADS=4 and other agents' runs going (load average 7 to 10).
Network / add-k / interpolation / mixed:
- 1: 3.593 +- 0.0016 / 3.599 / 3.612 / 3.594 (a tie with the pair model);
- 3: 2.576 +- 0.0087 / 2.659 / 2.632 / 2.550 (every seed lower);
- 5: 2.346 +- 0.0057 / 2.979 / 2.416 / 2.294 (every seed lower, by 0.07);
- 8: 2.360 +- 0.0090 / 4.654 / 2.409 / 2.283 (every seed lower, by 0.05).
The paper's claim held at 3, 5 and 8 characters, not at 1 (where there
is nothing to share between contexts). In perplexity at 5: 2^2.346 = 5.08
against 5.34, interpolation 5% above the network; the paper's table 1
(Brown corpus, words): 268 for its best network alone (MLP1), 252 mixed
with the trigram (MLP10, the one with the lowest validation perplexity),
312 for the best n-gram (class-based back-off, 24% above), 336 for deleted
interpolation of trigrams (33% above); AP News 109 against 117 (8%).
Their mix row is their best, as ours is. The network does not gain from 8 characters over
5 (2.360 against 2.346; a spike at 12, one seed: 2.451): more context is
more weights before the hidden layer, not more use. Embeddings in the
long run: '.' -> '!' 0.81, '?' 0.81; 's' -> 'S' 0.57; 'a' -> 'A' 0.32;
'A' -> 'a' 0.32, 'E' 0.29, 'O' 0.27; vowels near vowels only within noise.
Departures from the paper, for the page: characters, not words (65
symbols, where its vocabularies had 16,383 words (Brown) and 17,964 (AP
News), so the curse of dimensionality is milder and counting stronger);
Adam, not plain SGD; no direct connections; dropout in the long run (the
paper used weight decay, 1e-4 on Brown); the mix by fixed halves, as the
paper's; deleted interpolation with one weight per order (the paper's,
after Jelinek and Mercer 1980, has a set of weights for each frequency
bin of the context, also fit by EM on validation, and 1 / |V| as one of
the mixed models, where ours gives 1 / V for an unseen context);
Kneser-Ney (the paper's 321 to 323) not run. The paper's other finding,
that its network gained from 2 to 4 words of context while the n-grams
did not, is not ours: both gain from 3 to 5 characters, and the network
not from 5 to 8.
Tried and not used: smaller or shorter short runs (h 256, m 16, 3000
steps of 256: 2.75 at 5; h 512, m 24, 10000 steps of 256: 2.46, 9 s;
4000 of 1024 at lr 0.01: 2.444, 7 s, too slow for 3 seeds and 3
contexts); a long run without dropout (h 512, 30000 steps of 1024:
training 1.85, test 2.48, overfit); interpolation with 0 instead of 1 / V
after an unseen context (2.525 against 2.416 at 5, rerun for the page's
Break it, which changes that one line of NGram.probabilities: add-k inf
from 2 characters on, k = 1 chosen since every k is inf on validation, the
weights at 5 0.002 0.031 0.100 0.258 0.378 0.231, and with `"contexts=[5]"
seeds=1` the network, 2.482, now 0.043 below interpolation where it was
0.066 above; numpy prints two RuntimeWarnings, nplm.py lines 125 and 126 of
the project at 07.02; 8 to 10 s). Times: steps take 1.2
to 2.4 ms here with 512 units and 4 to 10 threads; with the machine busy,
10 threads were slower than 4 (oversubscribed: the 2500-step default took
68 s at load 9 to 13 with 10 threads, as much system time as user time,
and 37 s with OMP_NUM_THREADS=4).
Thread count and bytes: a run with 1 and with 10 threads gives different
bytes in summary.json (the 7th digit of a weight after 300 steps): the
order of float32 sums in a matrix product depends on the threads. Printed
numbers agree to every digit shown (checked at 4 and 10 threads). The
byte-for-byte test runs twice under the same conditions, so it holds.

**07.03 A recurrent network (Bengio, Simard and Frasconi 1994; Pascanu,
Mikolov and Bengio 2013).** models/rnn.py: RNNCell is tanh(ih(x) + hh(h)),
two Linear layers (so two biases, as torch.nn.RNN has); RNN loops over the
steps calling the cell (computing ih for every step at once outside the
loop was slower here: 12.2 against 8.9 ms for a batch of 64 x 64 steps at
256, forward and backward). The test copies torch.nn.RNN's weights in and
compares states and every gradient at 1e-10 in float64. nn.Linear's start
gives the recurrent matrix a spectral radius of about sqrt(1/3) = 0.58
(0.61 measured), nn.RNN's would differ (all weights in +-1/sqrt(hidden)).
rnn, default:
1. CharRNN (embeddings of 32, a state of 256, Linear to 65), truncated
   backpropagation through time: the training text as 64 streams laid end
   to end, 64 characters of each per step, the state carried and
   detached; Adam 0.005 falling to 0 on a cosine, 600 steps (2.5M
   characters, 2.4 passes), the gradient clipped to 1. Test bits (window_
   bits, spans of 1024, each scored character with 64 or more before it):
   2.545, 2.540, 2.536, `2.54 +- 0.0049` (the seeds change only the start:
   the streams are the same every run). Gradient length median 0.44 to
   0.45, largest 1.4 to 1.7, 5 or 6 of 600 steps clipped. At 800 steps, the
   first default (2.487, 2.487, 2.486; 57 to 73 s with 10 threads and the
   machine busy, so 600): with clip=0 the same bits (2.488, 2.473): the
   text network does not need clipping. Against 07.02: its best count
   model (interpolation up to 5) 2.416, its network at 5 (short run)
   2.474. So in a minute the RNN is behind both; say so. Spike (not in
   the default run): the same network for 5000 steps (79 s, 1 seed): test
   2.369, validation 2.183. Tried for the default: a state of 384 for 600
   steps (2.459, 2.457, 2.510: more spread, seed 2 clipped 41 steps) or 800
   steps (2.412, 1 seed, 17 s a seed, too slow for 3 seeds); 512 for 500
   steps (2.512: lr 0.005 is too high for it, 110 of 500 steps clipped);
   lr 0.01 at 256 (2.499, 32 clipped); 128 streams of 32 (2.483); a state
   of 128 for 1600 steps (2.611).
2. What it uses: each test character (every 4th from 64 on, 13,927) read
   after 64 characters of which only the last w are really the ones
   before it, the others the 64 before another, random position: w = 0
   10.037, 1 5.867, 2 4.337, 4 3.121, 8 2.633, 16 2.566, 32 2.567, 64
   2.567 (at 800 steps: 10.469, 6.074, 4.459, 3.126, 2.579, then 2.506
   three times). Past 16 characters nothing it reads changes its guess (to
   3 decimals, or the last one): that is the forgetting, on real text.
   (2.567 here against part 1's 2.545: every 4th character, and a window
   that starts with false text.) Small w are worse than
   the pair model and even than equal chances because the false text before
   them misleads it; the comparison that matters is where it stops
   changing. A first version started from a zero state and read only the
   last w (w = 1 5.211, 8 2.537, 16 to 64 2.506): the same 16, but a zero
   state is one it hardly saw in training.
3. The recall task: a symbol of 8, then T blanks (a ninth symbol), answer
   from the last state; Recall (embeddings of 16, a state of 64), SGD with
   momentum 0.9 at 0.1 (the papers' plain gradient descent; recall_opt=adam
   is there), 300 steps of 64, clipped to 1, 3 seeds, accuracy on 1000 new
   sequences: T = 2, 5, 10: 1, 1, 1 in every seed; T = 20: 0.624 +- 0.441
   (0.115, 0.881, and one between); T = 40: 0.169 +- 0.082 (0.115 to 0.264;
   chance 0.125). Clipping is needed here: with clip=0 (2 seeds) T = 10
   gives 0.131 (the loss jumps to 12.6 at step 100, an exploding step),
   T = 20 0.25, T = 40 0.12. With Adam (spike, lr 0.01, 5 seeds) the fall
   is softer and noisier: T = 20 0.83 (0.41 to 1.0), T = 40 0.42 (0.13 to
   0.75): Adam scales each weight's tiny gradient up to a full step, so the
   long path is not as starved; the gradient table still shows it is tiny.
   With random filler symbols instead of blanks (spike, Adam): 0.83 at 20,
   0.36 at 40, 0.45 at 80 (2 seeds): no cleaner.
4. The gradient reaching the input k steps back (k = 0, 5, 10, 20, 40, 60)
   for the recall task with T = 60, 256 sequences, gradient_back (the
   inputs' embeddings made a leaf, torch.autograd.grad, so no weight's
   .grad changes): as it starts (radius 0.61) 9.5e-4, 2.2e-5, 4.4e-7,
   2.1e-10, 1.1e-16, 4.1e-23; the same weights rescaled to radius 0.5:
   down to 7.3e-20 at 40 and 0 at 60; 1.0: 8.9e-4 to 2.0e-11; 2.0: 6.7e-4
   rising to 0.11; 3.0: 5.1e-4 rising to 2900. The trained text network
   (radius 2.95, on 256 windows of the test text): 3.4e-3, 3.7e-4, 3.7e-5,
   3.9e-7, 4.3e-11, 1.0e-14 (at 800 steps: radius 3.25, the same shape):
   it vanishes although the radius is above 1,
   because tanh saturates and its slope multiplies every step. Pascanu et
   al. state their conditions with the largest singular value of the
   recurrent matrix, which is at least its spectral radius (in a spike, 0.90
   at radius 0.5 and 1.79 at radius 1): below 1 the gradient must vanish
   (with tanh, whose slope is at most 1); above 1 it may explode, and need
   not. The column printed is the spectral radius, the size of the largest
   eigenvalue; do not call it the singular value. Exact zeros: at radius 0.5
   the gradient underflows float32 before 60 steps.
5. 300 characters, the state carried from one character to the next (a
   small Reader object as next_scores for sequences.sample), seed 0.
For the page (lessons agent), all with the code as committed:
- The longer run the page shows, `rnn steps=5000 seeds=1`: test 2.375 (not
  the spike's 2.369 above), 5 of 5000 steps clipped; what it uses: w = 8
  2.526, 16 2.388, 32 and 64 2.387 (still about 16 characters); the trained
  network's radius 6.35, its gradient 3.75e-03 at k = 0 to 5.74e-09 at 60
  (vanishing, more slowly); recall seed 0 at T = 20 0.115. 129 s of
  training and scoring (130 s wall) with another agent's runs going (load 9).
- The gradient's fall per step for the recall network as it starts: 0.46
  a step from k = 0 to 20, 0.49 from 20 to 40 (a fact on the page).
- Saturation in the trained text network (seed 0, the page's run, reading
  "First Citizen" from a zero state; the stepped figure): 83 of the 256
  state numbers beyond 0.9 in size after the first character, 139 to 189
  after each of the others, where tanh's slope 1 - h^2 is below 0.19.
- The page's Break it takes clipping out of train_recall only (the text
  network keeps its clip): T = 2 and 5 still 1; T = 10 0.13 +- 0.00404
  (every seed at chance); T = 20 0.249 +- 0.135; T = 40 0.249 +- 0.224 (0.115
  to 0.508). Seed 0's log at T = 10: loss 2.08 at steps 0 and 50, 12.6 at
  step 100 (gradient length 6.54), 2.25 at the end; clipped, the same seed's
  loss is 0.499 at step 100 and 0.0012 at step 299.
- torch.nn.RNN with our weights copied in gives the same states to 1e-12 in
  float64, and one step's backward equals (g * (1 - h_new^2)) @ hh.weight
  (the page's session, a check of its derivation).

**07.04 Attention (Bahdanau, Cho and Bengio 2015, figure 2).** models/
attention.py: attend(scores, values) = softmax over the last axis, then
weights @ values; Additive = v . tanh(W q + U k), no biases (their
appendix A.1.2 writes none: "whenever possible, we omit bias terms").
models/seq2seq.py: Encoder (embedding, 07.03's RNN), Decoder (07.03's
cell, starts from the encoder's last state, reads the previous symbol,
START numbered `symbols`), AttentionDecoder (scores of its state before
the step against every encoder state, attend, the context read beside the
previous symbol's embedding and given to the output beside the new state:
the paper's section 3.1, with its s_{i-1} as the query), Seq2Seq (forward
with teacher forcing, generate greedy, both returning the weights).
attention, default: copying 10 random symbols, trained on lengths 1 to 20
(each batch one length), embeddings of 32, states of 64, score size 64,
Adam 0.003, 1000 steps of 64, clipped to 1, 3 seeds; a line after each
model is trained (the last batch's cross-entropy, in nats: about 2 without
attention, 0.001 to 0.06 with); then the fraction of symbols written right,
greedily, on 500 new inputs of each length (rng 1000 + seed). No attention
/ attention (t):
2: 1.000 / 0.999 (-1.0); 5: 0.454 / 1.000 (+36.1); 10: 0.242 / 0.992;
15: 0.186 / 0.973; 20: 0.156 / 0.937; and longer than any trained on, 25:
0.142 / 0.874; 30: 0.129 / 0.801; 40: 0.125 / 0.604 (chance 0.10). Whole
outputs right: no attention 1.000 at 2, 0.010 at 5, 0 from 10; attention
0.999, 0.999, 0.973, 0.912, 0.809, 0.668, 0.497, 0.203. (At 1200 steps,
the first default, 43 to 49 s with the machine busy: 0.998 / 1.000, 0.471
/ 0.999, ..., 0.166 / 0.942 at 20, 0.125 / 0.665 at 40.)
The weights of one example of length 10 and one of 30 per attention seed
are in the summary.json of attention/seed<k> ("examples": input, written,
weights, one row per output step, each adding up to 1). Seed 0's printed
example (input 8 6 5 2 3 0 0 0 1 8) puts its most weight on input i at
step i every time, 0.73 to 0.99. Its length-30 example (longer than
trained on) is a clean diagonal for 13 steps, then loses its place: the
largest weights wander (positions 28, 20, 29, 9, ...) and 15 of the 30
symbols are wrong; at 1200 steps the same seed's was a clean diagonal but
for one step. A figure of both shows where attention holds and where it
does not.
Held: without attention the copy falls with length, from right at 2 to
near chance by 20; with attention it holds at the lengths trained on (0.94
at 20, the longest) and stays far above on longer ones, falling slowly
(0.60 at 40). The paper's figure 2 is BLEU against sentence length for
English to French: RNNencdec-30 and -50 fall as sentences lengthen,
RNNsearch-50 "shows no performance deterioration even with sentences of
length 50 or more" (table 1: BLEU 17.82 against 26.75 on all sentences).
Ours is not translation and not BLEU; and past the trained lengths ours
does deteriorate, which theirs (trained to 50, scored to about 60) shows
less of. Departures: the paper's units are gated (its appendix A.1.1),
ours 07.03's tanh cell (no LSTM or GRU in this module); its encoder is
bidirectional, ours one-way, so that the only change is in the decoder;
its output is a maxout layer, ours Linear; it searches with a beam, we
decode greedily. No attention needs more than 1000 steps even at short
lengths (spike, 6000 steps, 1 seed: 0.96 at 3, 0.56 at 5, 0.30 at 10,
0.19 at 20; a state of 128, 3000 steps: 0.98, 0.60, 0.30, 0.18): more
training does not save it past 5. task=reverse (spike, 2 seeds) is the
more paper-like curve for the plain model, which reverses short inputs
well (1.00 at 5, 0.80 at 10, 0.41 at 20, 0.26 at 40) while attention gives
1.00, 0.99, 0.87, 0.42: it holds less well than on the copy (a one-way
encoder's states know less of what comes after them); the default stays
the copy, where attention holds.
For the page (lessons agent): attention.py's table now pads each spread to
48 characters (they ran to 48 and broke the columns at 38); no number
changed. The default run took 69 s once with another agent's runs going
(37 to 38 s before). Seed 0's length-30 example: the largest weight is on
input i for steps 0 to 12, then on positions 28, 20, 29, 9, 17, ...; 15 of
30 written wrong (step 11 is wrong on the diagonal too). attend() on scores
0, 1, 2 over values 1, 2, 3: weights 0.09, 0.2447, 0.6652, sum 2.5752 (a
session on the page). The page's Break it makes attend's weights equal
(`torch.full_like(scores, 1 / scores.shape[-1])`): the attention models'
last batch 1.0 to 1.5 nats; symbols right 1 at 2, 0.804 at 5 (t = +14.1
against no attention: the mean of the encoder states is more than its last
state), 0.3 at 10, then no better than without (0.154 at 20, 0.119 at 40);
whole rows 0.595 at 5, 0.001 at 10. Seed 0 writes 2 8 0 5 6 0 3 8 0 1 for 8
6 5 2 3 0 0 0 1 8: the input's symbols, each as often, in another order.
43 s. models/rnn.py's docstring no longer mentions the test (the site
shows it): it says that copying one's weights into the other gives the
same states.

### Module 08: the transformer, a GPT

models/gpt.py is built over 08.01 to 08.03 and is the file modules 09 to
14 start from (see "For module 09 and after" below for its names, the
GPT-2 mapping and how to use it). Regions: causal_mask, self_attend,
SelfAttention (08.01); gelu, MLP, Block, GPT (08.02); Positions (08.03).
@from blocks: SelfAttention gains `heads` at 08.02 (its signature, the
cut into heads in qkv, the join in forward); GPT gains `positions` at
08.03 (its signature, the Positions it makes, the add in embed). The
docstring's later lines carry one-line `# @from` markers, as data/fetch.py's
does. Every experiment of the module builds the model its own settings
name, so its numbers do not move when a later lesson changes the file:
08.01's OneHead uses SelfAttention with heads left at 1, and 08.02's GPTs
pass positions=False from 08.03 on (an @from block in heads.py's build).
Measured: self_attention at 08.01 and heads at 08.02 give the same bytes
in log.jsonl and summary.json in the project at their lesson and at the
end of the track.

What the learner already built is used under its name: layer norm
(04.04, nn.LayerNorm, eps 1e-5 as GPT-2's), residual connections (04.05,
the adds in Block.forward), AdamW (03.04), warmup and cosine decay
(03.05, lab.warmup_cosine through LambdaLR), dropout (05.02, F.dropout),
gradient clipping (07.03, clip_grad_norm_), embeddings (07.02,
nn.Embedding), attend (07.04), bits, windows and window_bits (07.02,
07.03), sample (07.02). New in the module: self-attention, heads, GELU,
the block, tied output, GPT-2's start, learned positions, top-k, top-p.

experiments/language.py is the module's shared loop (NOTES on 07 asked
for one outside the experiments): train(model, cfg, run, dev, ids,
held=None) (08.01; `held` from 08.04): each step cfg.batch windows of
cfg.context characters from random places (run.rng), bits, AdamW with
weight decay on the tensors of 2 or more dimensions only (matrices and
embeddings, as nanoGPT does; biases and layer norms none), the
rate warmed up over cfg.warmup steps then a cosine to 0, clipped to
cfg.clip; a log row every cfg.every steps. attention_maps and looks
(08.02); held_bits, save and load (08.04); top_k, top_p and generate
(08.05).

GPT starts as GPT-2 does, as nanoGPT reads it: every weight normal with
sd 0.02, biases 0, layer norms 1 and 0, attention's out and the MLP's
down by 1/sqrt(2 x layers) smaller. Read at the sources: Radford et al.
(2019), section 2.3, "We scale the weights of residual layers at
initialization by a factor of 1/sqrt(N) where N is the number of
residual layers" (two to a block, so N = 2 x layers); OpenAI's
src/model.py draws every conv1d weight with sd 0.02, wte with 0.02, wpe
with 0.01 (ours: 0.02; and the 1/sqrt(N) is not in that file, which has
no training code). With the output tied to the embedding, nn.Embedding's
own start (sd 1) would give scores of sd about sqrt(width) and a first
loss far above log2 65 (reasoned, not measured; not a lesson).

**08.01 Self-attention with a causal mask (Vaswani et al. 2017, section
3.2.1).** experiments/self_attention.py: OneHead (an embedding of 128, one
SelfAttention of width 128, a Linear layer to the 65 scores), windows of
32 characters, batches of 32, 600 steps, AdamW 0.003 with weight decay 0.1,
50 steps of warmup then a cosine, clipped to 1, 3 seeds.
1. The footnote in numbers (queries and keys of d numbers of variance 1,
   1000 queries over 32 positions): the sd of q . k is 3.99, 7.91, 15.99,
   31.77 at d = 16, 64, 256, 1024 (sqrt(d)); the mean largest softmax
   weight 0.630, 0.812, 0.912, 0.951; the gradient back through the
   softmax (the length, for a random weighting of its output) 2.51e-01,
   1.73e-01, 9.20e-02, 5.13e-02. Divided by sqrt(d): sd 1.01, 1.00, 1.00,
   0.99, largest weight 0.163 to 0.165, gradient 2.27e-01 to 2.32e-01 at
   every d. Trained: divided `3.581 +- 0.006225`, not divided `3.752 +-
   0.02092`, t = +13.6. At width 64 (spike, 600 steps of windows of 64)
   the trained difference was nothing (3.649 against 3.660, t = +0.8), at
   128 it shows (3.604 against 3.771, t = +7.9), and at 256 (1500 steps)
   3.588 against 3.859, t = +8.2: the division matters once a head is
   wide, as the paper's "for large values of d_k" says. Our q and k come
   from nn.Linear's start (variance about a third of their input's), so
   their scores' sd is about sqrt(d)/3, not the footnote's sqrt(d).
2. The mask. Changed from the plan's failure, which needs positions: the
   plan said the loss without the mask falls towards nothing. Without
   positions (they are 08.03's) a query cannot find the next position:
   keys are made from what is at a position, not where, so the unmasked
   model sees the window as a bag of characters that includes the ones to
   come, and its loss falls only a little below the masked model's.
   Measured (bits per character): the last training batch, masked `3.527
   +- 0.04386`, no mask `3.25 +- 0.05688` (t = -6.7); the test text read
   as in training (every position of windows of 32, the future in view
   without the mask) `3.567 +- 0.008395` against `3.259 +- 0.07179` (t =
   -7.4); the test text, each character from the 32 before it only (the
   window that ends before it, its last position's scores: last_bits),
   `3.581 +- 0.006225` against `4.2 +- 0.08714` (t = +12.3). So the
   lesson's failure as found: the loss says the unmasked model is better,
   on held-out text too, and asked honestly it is far worse. Its text
   (seed 0, 300 characters after a newline) falls into one character
   ("thy hm me me m my? me me m ... rrrrrrrrr..."): longest run of one
   character 75, against 4 for the masked model's and 2 in the test text;
   07.02's count model (interpolation up to 5) scores it 5.581 bits per
   character against the masked model's 5.232 and the test text's 2.416.
   The samples are not noise, as the plan expected: they are one
   character over and over. Spike with learned positions added (the 08.01
   one head, width 64, windows of 64, 1500 steps, 2 seeds; scratch code,
   not in the project): without the mask the training batch falls to 0.068
   and 0.061 bits and validation to 0.064 and 0.065 (it copies the next
   character), with the mask 3.32 and 3.43; it writes newline after
   newline. That is the plan's failure, and 08.03 can show it if the page
   wants it (it would need a OneHead with positions; not built).
3. A window of 32 test characters with its last changed: masked, the
   largest change in the scores at the 31 positions before it 0, positions
   changed 0; no mask 1.01, all 31.
15.2 and 15.1 s with 10 threads at load 5 to 6 (a virtual machine taking
4 to 5 cores); 32 s at load 12.5; the same digits each time, and the
same as a run with OMP_NUM_THREADS=4. The plan's "A test: changing a later token
leaves every earlier output unchanged, exactly" is held by the tests of
08.01 (SelfAttention, OneHead), 08.02 (GPT without positions) and 08.03
(GPT with positions): torch.equal, not a tolerance.
Paper, read at the source (arXiv 1706.03762v7): "We suspect that for
large values of d_k, the dot products grow large in magnitude, pushing
the softmax function into regions where it has extremely small
gradients. To counteract this effect, we scale the dot products by
1/sqrt(d_k)." Footnote 4: "To illustrate why the dot products get large,
assume that the components of q and k are independent random variables
with mean 0 and variance 1. Then their dot product, q . k = sum_{i=1}^{d_k}
q_i k_i, has mean 0 and variance d_k." The divisor is the head's size,
d_k, which is the width only with one head (08.02 divides by width /
heads). Section 3.2.3 is where the paper masks: "We need to prevent
leftward information flow in the decoder to preserve the auto-regressive
property. We implement this inside of scaled dot-product attention by
masking out (setting to -inf) all values in the input of the softmax
which correspond to illegal connections." (Its -inf is the symbol; every
quote here was checked against the PDF.)

**08.02 Many heads, and the residual stream (Vaswani et al. 2017,
section 3.2.2 and table 3).** experiments/heads.py: width 64, windows of
32, 300 steps of 32, AdamW 0.003, 3 seeds; no positions (08.03). Bits per
character on the test text, each character with 16 or more before it:
1. The obvious way deeper, 08.01's attention layer after layer (Stack: an
   embedding, SelfAttention after SelfAttention, a Linear layer): 1 layer
   25,025 weights `3.727 +- 0.02901`, 4 layers 74,945 `4.598 +- 0.005443`,
   t = +51.2. Four are far worse than one (the four sit near 4.6, worse
   than single-character counts' 4.85 only a little).
2. Blocks (pre-norm: x + attention(norm1(x)), then x + mlp(norm2(x)), a
   last layer norm, tied output): 1 block of 4 heads 54,272 weights `3.503
   +- 0.005772`, 4 blocks 204,224 `3.407 +- 0.009038`, t = -15.4.
3. Heads at the same weights: 4 blocks, 1 head of 64 `3.433 +- 0.01583`,
   4 heads of 16 `3.407 +- 0.009038`, t = -2.4: four heads a little better,
   not beyond doubt at 3 seeds. The paper's table 3 rows (A) (English to
   German, dev perplexity per word piece / BLEU): h = 1 5.29 / 24.9; 4
   5.00 / 25.5; 8 (base) 4.92 / 25.8; 16 4.91 / 25.8; 32 5.01 / 25.4; its
   text: "While single-head attention is 0.9 BLEU worse than the best
   setting, quality also drops off with too many heads." Rows (C), depth: N
   = 2 6.11 / 23.7, 4 5.19 / 25.3, 8 4.88 / 25.5 (base 6). Ours points the
   same way at a far smaller size, the heads less clearly.
4. Where each head looks (seed 0 of 4 blocks of 4 heads, 575 windows of
   the test text, positions 16 to 31; how far back on average, the weight
   on its own position, on the one before): block 1 all four heads near
   equal weights (11.1 to 11.7 back, 0.04 to 0.06 each; equal weights would
   be 11.8 and 0.04); deeper blocks a little sharper (block 3, a head at
   0.16 on itself, another 8.4 back). Without positions a head can choose
   only by what is at a position; the little sharpening in deeper blocks
   is the order the mask lets in (08.03, part 1). Seed 0's weights on the
   first 32 test characters are in runs/heads/blocks4-heads4/seed0/
   summary.json ("window": the 32 character numbers; "weights": 4 blocks
   x 4 heads x 32 x 32, 4 decimals): the figure's data.
Tried: 500 steps (3 seeds, OMP_NUM_THREADS=4, the machine busy, 109 s):
stack 3.635 / 4.521 (t = +41.3), blocks 3.460 / 3.293 (t = -27.5), heads
3.331 / 3.293 (t = -3.7), the same story; at 2 layers and 500 steps the
stack's failure is small (3.635 against 3.680, t = +2.1) and the heads
3.412 against 3.380 (t = -4.3); with 16 heads of 4 (2 blocks, 600 steps,
windows of 64) 3.361 against 4 heads' 3.385 and 1 head's 3.417, and twice
the time of one head. The default is 4 layers at 300 steps for the
minute.
46.8 and 44.8 s with 10 threads at load 5 to 6 (a virtual machine taking
4 to 5 cores); 101 s at load 12 to 14 (80 s of it system time: the 10
threads fighting for cores); 45 s with OMP_NUM_THREADS=1 at load 5 to 8.
The same digits every way. The slowest default of the module; fewer
steps or layers=3 would shorten it, with what effect on the table not
measured.
Cut to 2 seeds by the lessons agent (the plan's rule: verifying, at load
10 to 13 with another agent training, the 3-seed default took 82 s, over
55; 08.01's took 44 s there against its 15 to 17). The default is now
seeds=2 (heads.py CONFIG): 1 attention layer `3.715 +- 0.02878`, 4 layers
`4.597 +- 0.007313`, t = +42.0; 1 block `3.503 +- 0.007851`, 4 blocks
`3.406 +- 0.01263`, t = -9.2; 4 blocks of 1 head `3.43 +- 0.02069` against
4 heads, t = -1.3 (within the noise at 2 seeds; the 3-seed numbers above
are `heads seeds=3`, which 08.02's page runs again, trimmed to part 3);
part 4 is seed 0's and unchanged. 44 s at load about 10 (the same run, 3
seeds, 82 s); at load 6 not timed (two thirds of 45 s would be 30). The
test already ran
heads with seeds=2, so it is unchanged. 08.03's positions.py keeps 3
seeds: its no-positions row (3.407) is the 3-seed number, not 08.02's
default any more.

**08.03 Where am I: position embeddings (Vaswani et al. 2017, section
3.5).** experiments/positions.py, the same settings as 08.02 (4 blocks of
4 heads, width 64, windows of 32, 300 steps, 3 seeds).
1. The plan's exact test does not hold as stated for a GPT of more than
   one block, and the lesson changes: the scores at the last position are
   the same for any order of the characters before it only with one block.
   Measured in float64, the last of 32 test characters, the 31 before it
   in 5 other orders: 1 block without positions, the largest change in a
   score 3.55e-15 (2.66e-15 in another run: rounding); 4 blocks without
   positions 2.44; 4 blocks with learned positions 4.24. Why: in one block
   the last position's query meets a set of keys and values, each made
   from one character alone; from the second block on, each position's
   vector holds what its first-block attention saw, and with the mask that
   is the characters up to it, which depends on the order. The causal mask
   gives the model order without any positions. Haviv, Ram, Press, Izsak
   and Levy (2022), "Transformer Language Models without Positional
   Encodings Still Learn Positional Information" (arXiv 2203.16634; its
   abstract read, not the paper): causal language models without
   positions "are still competitive with standard models", and "We
   conjecture that causal attention enables the model to infer the number
   of predecessors that each token can attend to, thereby approximating
   its absolute position." The test holds the one-block case at 1e-12 and
   the two-block and positions cases above it.
2. Bits: no positions `3.407 +- 0.009038` (the same models as 08.02's 4
   blocks of 4 heads: same settings and seeds), learned positions `3.342 +-
   0.009945`, t = -8.4. Positions help, by 0.065 bits at this size, not by
   the gulf the bag-of-characters picture suggests (part 1 says why).
3. Past the context length (seed 0): with learned positions a window of
   128 is "ValueError: 128 positions, but there are learned vectors for
   32" (Positions refuses it; nn.Embedding would have raised an
   IndexError); read with only the last 32 before each character it scores
   3.351. Without positions any length runs: windows of 32, 64 and 128 from
   the test text, bits at positions 0 to 31 / 32 to 63 / 64 to 127: n = 1
   3.399; n = 2 3.410 / 3.537; n = 4 3.410 / 3.543 / 3.682. Worse the
   further past the trained length: what it learned of order from the mask
   is tied to the lengths it saw. The paper chose sinusoids "because it may
   allow the model to extrapolate to sequence lengths longer than the ones
   encountered during training", and found learned ones "nearly identical"
   (table 3 row (E): 4.92 / 25.7 against the base 4.92 / 25.8); sinusoids
   are not built here; module 10's rotary positions are the track's answer.
4. Where the heads look with positions (seed 0): block 1's heads now
   differ (8.0, 7.9, 11.0 and 5.2 back; one head 0.14 on itself and 0.16
   on the one before); no head is a clean "previous character" head after
   300 steps. The models are short-trained. 08.04's long-run model was not
   looked at this way (attention_maps takes any GPT, and load() gives
   one back from its checkpoint).
38.9 and 38.9 s with 10 threads at load 6 to 7 (a virtual machine taking
4 to 5 cores); 88 s at load 13 to 14; 39 s with OMP_NUM_THREADS=1 at load
3 to 5. The 08.01 failure with positions (spike under 08.01, part
2) belongs here if the page wants the plan's dramatic version.

**08.04 Training a GPT on Shakespeare.** experiments/gpt.py: GPT with
learned positions trained by language.train (AdamW, weight decay 0.1 on
the matrices and embeddings, warmup then cosine to 0, clipped to 1),
each of `dropouts` for `seeds` seeds; every `every` steps the bits of a
fixed batch of `held` validation windows (rng 0) go to the log beside
the training batch's (train's held, held_bits). Scored at the end with
window_bits, each character with context / 4 or more before it, on the
test text and on the validation text. 07's ladder is printed first: the
count models computed again (ladder: equal chances 6.022, single
characters 4.850, pairs 3.599, add-k best on validation context 4 with k
0.03 2.629, deleted interpolation up to 7 2.409: 07's own numbers to the
last digit), its networks quoted from their runs (NETWORKS in gpt.py:
2.474, 2.346, 2.294, 2.283, 2.540, 2.369). The checkpoint: the model with
the lowest validation bits of the run, saved with save() to
<out>/gpt/model.safetensors (metadata: config, steps, seed, val_bits),
loaded back with load(), the same scores (torch.equal); then 500
characters from it (07.02's sample, temperature 1, seed 0).
The default (short) run: 4 blocks of 4 heads, width 64, windows of 64
(208,320 weights), 300 steps of 32 (0.6 passes), AdamW 0.003, warmup 50,
2 dropouts x 2 seeds: dropout 0 test `3.332 +- 0.01587` (validation
3.322), dropout 0.2 `3.474 +- 0.004561` (3.475), t = +12.1; every
validation curve lowest at its last point (step 299); checkpoint dropout
0, seed 1, the same scores loaded back. Below the pair model, far above
every model of 07 but the pair and single counts: in a minute the GPT
has not caught up (it has seen 0.6 of the text once). Its text is
07.01-like gibberish with speakers' names and line breaks. 35.1 and 33.0
s with 10 threads at load 5 to 6. The page's Run it shows the table and
dropout costing; where validation turns up, and dropout curing it, are
the long run's (no minute of CPU gets near 15 million characters).

The long run, recorded in experiments/recorded/gpt/ (config.json,
log.jsonl and summary.json of each dropout and seed; curves.svg, every
run's training batch dashed and validation windows solid; output.txt,
what it printed). Its checkpoint (model.safetensors, 10.9 MB) was moved
out: no weights are shipped.

    python3 -m experiments.gpt layers=6 heads=6 width=192 context=256 batch=32 steps=2800 lr=0.002 warmup=100 every=100 seeds=2 out=experiments/recorded

6 blocks of 6 heads, width 192, windows of 256 (2,731,200 weights), 2800
steps of 32 windows (22.9 million characters, 22.8 passes), AdamW 0.002,
weight decay 0.1, warmup 100 then cosine to 0, clipped to 1; dropout 0
and 0.2, 2 seeds each. 3371 s by its own clock, 56 min 12 s of wall clock
(18:16:30 to 19:12:42), 10 threads, a virtual machine taking 4 to 5
cores and other agents' runs coming and going (load 5 to 11; a step took
0.29 to 0.32 s, dropout's a little longer). Two seeds, not three: three
would have been about 85 minutes; four runs of 2800 steps were what the
hour holds, and 2800 is what it takes to see the curve turn.
Bits per character, each character with 64 or more before it:
- dropout 0: test `2.361 +- 0.02564` (2.343, 2.379), validation `2.098 +-
  0.01694` (2.086, 2.11). The validation windows' curve is lowest at step
  1800 (2.040) and 2000 (2.027), then rises to 2.089 and 2.056 at the end;
  the last training batch 1.45 and 1.55 bits.
- dropout 0.2: test `2.226 +- 0.01542` (2.216, 2.237), validation `2.015
  +- 0.01929` (2.002, 2.029). The curve still falls, or is flat, at the
  end (lowest 1.998 at 2600, 2.027 at 2799); the last training batch
  (with the dropping) 1.83 and 1.91.
- dropout 0.2 against 0, test: t = -6.4.
Where validation turns up: without dropout, at about step 1800 to 2000,
after 15 to 16 million characters (15 to 16 passes over the training
text), while the training batch keeps falling: from there the model
learns the training plays at the cost of the held-out ones (0.03 to 0.05
bits back up on the validation windows by the end, and its test bits
2.361 against 2.257 for the same model stopped at 1500 steps, below).
What dropout does about it: with dropout 0.2 the curve does not turn up
in 2800 steps, and the model ends 0.08 bits lower on validation and 0.135
lower on test than without; the gap between the training batch and the
validation windows is about 0.15 bits at the end against 0.5 to 0.65
without.
The checkpoint is dropout 0.2, seed 0 (the lowest validation bits,
2.002).
Beside 07's ladder (test): equal chances 6.022, single characters 4.850,
pairs 3.599, add-k context 4 2.629, interpolation up to 7 2.409; 07.02's
network 2.474 (short) and 2.346 (long), mixed with interpolation 2.294 (5)
and 2.283 (8); 07.03's recurrent network 2.540 (short) and 2.369 (5000
steps, 1 seed). The GPT chosen on validation (dropout 0.2): both seeds
below every one of them; the mean 0.057 below 07's best (the mix at 8;
the worse seed 0.046), 0.120 below 07.02's network alone, 0.143 below the
recurrent network's 5000 steps, 0.183 below interpolation. In perplexity
per character 2^2.226 = 4.68 against 2^2.283 = 4.87, 4% lower. Without
dropout, run this long, it is worse than 07.02's network mixed with
interpolation (2.361 against 2.283), and than 07.02's network alone
(2.346): overfitting has given back all of the gain. The
test holds the turn-up without dropout, dropout's lower validation bits,
and every seed of the chosen setting below 2.283.
The text (dropout 0.2, seed 0, 500 characters after a newline) has verse
lines, capitals, speakers' names (POLIXENES, AUTOLYCUS: The Winter's
Tale's, in the training text), real words in Shakespeare's rhythm, and
some made ones ("cheech", "muzzer", "disvolutation"): "thou makest awhile
fild can examply in the strength / our conduction. / My son of bloody
Coriolanus Capulet, / He reign with committed, true nember their peace /
And almost behind a cheech to muzzer thee. / So I fearful free it, my
lord, say, if thou dost of wine." Passable verse at a glance, as the
outline asks; not sense.
An earlier recording, replaced by this one (the same settings but 1500
steps; 29 min 26 s, load 5 to 18): dropout 0 test `2.257 +- 0.005479`
(2.253, 2.261), validation 2.052, the curves lowest at their last point;
dropout 0.2 test `2.378 +- 0.01022`, validation 2.211, t = +14.7. At
1500 steps nothing had turned up and dropout only cost (0.12 bits on
test). It was replaced because it could not show what 08.04 is about
(where validation turns up and what dropout does), and an hour held a
run that does. Its numbers say something too: the best of the four runs
without dropout is the one stopped at 1500 steps (2.257 on test, against
2.361 at 2800); stopping early does part of dropout's job, and dropout at
2800 steps does better than either (2.226). The 1500-step text: "Thy
father had self Warwick exhally daregels, / Bear of thy hounty here hath
good beheld!".
Spike, the size and the length (what I tried). Explored on the Apple GPU
(mps) for speed, each run given the steps the CPU makes in 570 s (9.5
minutes) at its CPU time a step (10 threads, load about 4: 107, 162, 240,
390, 523 ms for the sizes below), windows of 256, batches of 32, lr 1e-3,
warmup 100, weight decay 0.1, 1 seed; validation / test bits at the end:
- 4 blocks of 4 heads, width 128 (834,432 weights), 5327 steps: 2.054 /
  2.287; dropout 0.2: 2.169 / 2.349.
- 4 x 192, 6 heads (1,841,472), 3518 steps: 2.076 / 2.291; 0.2: 2.124 /
  2.311.
- 6 x 192, 6 heads (2,731,200), 2375 steps: 2.038 / 2.259; 0.2: 2.149 /
  2.337.
- 6 x 256, 8 heads (4,821,248), 1461 steps: 2.065 / 2.242; 0.2: 2.255 /
  2.418.
- 6 x 384 (10.8M): not measured (its run was stopped by mistake).
In every one the validation windows' curve was lowest at its last point:
within 9.5 minutes of CPU nothing turns up, and dropout 0.2 only costs.
Where it does turn up (mps, no dropout unless said): 6 x 192 at lr 1e-3
with the cosine stretched over 10000 steps (stopped at 3000): lowest 2.133
at step 2500, then 2.179 and 2.185 (training batch 1.61); 6 x 192 at lr
2e-3, cosine over 3700 (stopped at 2400): lowest 2.113 at 2100, 2.161 at
2400; 6 x 256 at lr 1e-3 over 2300: lowest 2.101 at 1800, 2.103 at the
end, and test 2.290, worse than the same model's 2.242 after 1461 steps
(the longer run fits the training plays better and The Tempest worse);
with dropout 0.2 the same model was still falling at 1800 (2.165), behind.
So on this text a GPT of a few million weights starts to overfit after
about 15 to 20 million characters (15 to 20 passes): four runs of 1500
steps (12 million each, the first recording) fall just short of it, four
of 2800 (the recording) go past it.
Longer still (mps, 1 seed, the long run's settings but 3700 steps, the
cosine over all of them; 431 and 397 s on mps, 18 to 20 minutes a run on
this CPU at 0.29 to 0.32 s a step): dropout 0.2 ends at validation 1.987,
test 2.225, its validation windows still falling at the end (lowest 2.035
at 3300; training batch 1.73); without dropout the curve is lowest at
1700 (2.110) and higher at every point after (2.129 at 2000, 2.193 at
2400, 2.319 at 3000, 2.385 at the end), the training batch down to 1.207
bits: validation 2.349, test 2.618, worse than 07.02's deleted
interpolation (2.409) and about level with its best add-k (2.629). The
same story as the recording, louder: test 2.225 against 2.618. The
recording at 2800 steps with dropout (2.226) is as good as this longer
run's (2.225).

**08.05 Sampling: temperature, top-k and top-p (Holtzman et al. 2020).**
experiments/sampling.py. The functions are experiments/language.py's:
top_k(scores, k), top_p(scores, p) (the nucleus: in order of chance, a
symbol is kept while the chances before it add up to less than p, so the
fewest whose chances reach p; equal chances in symbol order, sort's
stable=True), generate(model, prompts, n, generator, temperature, k, p)
(batched, temperature then top-k then top-p, as transformers orders
them; temperature 0 is greedy). The model: the checkpoint 08.04 leaves
(experiments/recorded/gpt/model.safetensors when the learner has rerun
the long run with the recorded command, else runs/gpt/model.safetensors
from 08.04's default run), else, with none (as in verify, which replays
each lesson in its own copy), a GPT trained here: 4 blocks of 4 heads,
width 64, windows of 64, 600 steps, seed 0. checkpoint=PATH takes one,
checkpoint=none never does (the test uses it, so a learner's runs/ cannot
change what it checks). The output's first line says which.
16 prompts: the first 32 characters of 16 speeches of the test text,
evenly spread (a speech starts after a blank line); 200 characters after
each; 3 seeds of the sampling (greedy once: it has no chance in it).
Perplexity: 2 to the model's bits per character of the 200 (its own
chances, before any cut; each character scored from at least the 32
before it, in windows as 07.03's window_bits). Repetition: the paper's
(its figure 9: "A phrase (minimum length 2) is considered a repetition
when it repeats at least three times at the end of the generation"), on
characters.
The default run (the small model):

    the text itself    8.898                       0.0%
    greedy             2.766 (no chance in it)     100.0%
    pure sampling      9.128 +- 0.1918 (3 seeds)   0.0%
    sampling, t=0.9    7.688 +- 0.05169            0.0%
    sampling, t=0.7    5.821 +- 0.1142             0.0%
    top-k=5            5.232 +- 0.1573             0.0%
    nucleus, p=0.95    7.512 +- 0.2581             0.0%

Greedy ends in a loop after every prompt (both passages shown: " the the
the ..."; perplexity 2.77, a third of the text's 8.90). Pure sampling is about as unlikely to the
model as the text itself (9.13 against 8.90, 2.6% above); every cut makes
the text more likely to the model (t=0.9 7.69, nucleus 0.95 7.51, t=0.7
5.82, top-k 5 5.23). The closest to the text is pure sampling, not the
nucleus. No sampled passage of 200 characters ends in a loop.
The paper's table 1 (GPT-2 Large, 5,000 passages of up to 200 word
pieces, WebText; perplexity / repetition %): human 12.38 / 0.28; greedy
1.50 / 73.66; beam b=16 1.48 / 28.94; stochastic beam 19.20 / 0.32; pure
sampling 22.73 / 0.22; sampling t=0.9 10.25 / 0.66; top-k=40 6.88 / 0.78;
top-k=640 13.82 / 0.28; top-k=40, t=0.7 3.48 / 8.86; nucleus p=0.95 13.13 /
0.36. Its claims, quoted from the paper (arXiv 1904.09751v2): abstract,
"maximization-based decoding methods such as beam search lead to
degeneration - output text that is bland, incoherent, or gets stuck in
repetitive loops" (its dash); section 4.2, "We see that perplexity of
text obtained from pure sampling is worse than the perplexity of the
gold. This indicates that the model is confusing itself", and "Nucleus
Sampling obtains closest perplexity to human text, as shown in Table 1";
figure 9, "Sampling with temperatures lower than 0.9 severely increase
repetition".
What held at this size: greedy's degeneration (held, strongly: every
passage a loop, perplexity a third of the text's; the paper's 73.66%).
What did not: pure sampling's text is only a little less likely to the
model than the text (its perplexity 2.6% above, where the paper's is 84%
above), and so the nucleus,
which cuts the tail, moves the text further from the text's perplexity
(7.51 against 8.90), not closer; and low temperatures do not loop on
characters in 200 steps. Why, as far as measured: with 65 characters the
tail the nucleus cuts is small (the paper's argument is about tens of
thousands of word pieces, each unlikely, together a large share), and a
character model's own perplexity is small to begin with. Top-k at the
paper's k = 40 cuts 25 of 65 characters, almost nothing of the
distribution: spike (the same model and seeds), top-k=40 gave 8.991
against pure sampling's 9.128, its first passage the same as pure
sampling's for its first 100 characters (the same draws until a cut
character would have been drawn); and top-k=40 with t=0.7 the same as
t=0.7 alone (5.823 against 5.821), the same first passage. So the default
lists top-k=5 instead, and the page should say why. Beam search, Self-BLEU,
the Zipf coefficient and HUSE are not run.
With 08.04's long-run checkpoint (`checkpoint=` the file the long run
saved: dropout 0.2, seed 0, 6 blocks of 6 heads, width 192, windows of
256, 2800 steps, validation 2.002; 85 s, not a default run), the same
prompts and seeds:

    the text itself    4.908                       0.0%
    greedy             1.867 (no chance in it)     0.0%
    pure sampling      3.195 +- 0.0529 (3 seeds)   0.0%
    sampling, t=0.9    2.859 +- 0.03311            0.0%
    sampling, t=0.7    2.565 +- 0.05808            0.0%
    top-k=5            2.654 +- 0.1118             0.0%
    nucleus, p=0.95    2.911 +- 0.06012            0.0%

With the better model even pure sampling writes text the model finds far
more likely than the text itself (3.20 against 4.91): the paper's
"perplexity of text obtained from pure sampling is worse than the
perplexity of the gold" does not hold here at all, and the nucleus is
again further from the text than pure sampling (2.91). Greedy is still
the most likely (1.87) and starts to repeat ("What shall I see the state
of the state of the world?", "And thou art the state of thy soul state,
/ And thou art the state of thy so") but no passage ends in a phrase
three times over within 200 characters: the paper's measure counts only
loops at the end. Part of why pure sampling is so far below the text:
the test text (the end of The Shrew, then The Tempest, whose names the
model never saw; 07's Data: every model is 0.2 bits worse on test than
on validation) is harder for the model than its own writing. Spike
(scratch code: the same functions on 16 speeches of the validation text,
3 seeds): the text itself 3.653, pure sampling `3.189 +- 0.1307` (min
3.093, max 3.338): still 13% below the text, beyond the spread. With the
first recording's checkpoint (dropout 0, 1500 steps, validation 2.049)
the same spike gave 3.724 against `3.547 +- 0.1945` (5% below, within
the spread), and the test table text 5.025, greedy 2.224, pure sampling
3.481, t=0.9 3.224, t=0.7 2.739, top-k=5 2.819, nucleus 3.125. So the
model trained with dropout finds its own samples more likely, against
the text, than the one without; why is not measured. The paper's human
text was from the same distribution as GPT-2's training data (held-out
WebText), so validation is the fairer ground; the experiment keeps test,
as the track scores everything on test, and the page should say so. The
paper's 84% above is seen with neither model nor text. The texts are
visibly better than the small model's (prompt 1, pure sampling: "Of
fortune misinously house I say. / Thou liest me thou, to a bed, I love
thee."; t=0.7: "but I'll not swear / What shall say you to the
conveyary of a / bed better in the sun of conscience").
The test checks the cuts against a direct computation on small scores,
generate against an argmax loop and against counted draws from a fixed
distribution (4000 draws, within 0.03), and the short run's story:
greedy below half the text's perplexity and looping in half the passages
or more, pure sampling within 15% of the text, t=0.7, top-k=5 and the
nucleus each below 95% of pure sampling's.
35.0 and 36.9 s with 10 threads at load 5 to 7 (a virtual machine
taking 4 to 5 cores); 72 and 110 s earlier at load 10 to 16 with other
agents' runs going. The same output each time.

**The pages (module 08's lessons agent, 2026-11-24).** The lessons are in
lessons/08-transformer/ (slug as 06-images, 07-language-models), with the
module page, cover and icon (art/outlines/research_art.py now reads
08.04's recorded run and asserts its numbers) and 18 figures from
art/research/figs08.py (about four minutes of runs; RESEARCH_FIGS_CACHE
keeps them). The generator trains three models again in the project at
their lesson, 08.01's masked OneHead (seed 0), 08.03's GPT with
positions (seed 0) and 08.05's small model, and stops unless each scores
what the page's run printed. Every default run printed on the pages gave
the digits above, run by run (08.02 in 45 s at load 6 to 7; then 82 s
when verifying at load 10 to 13, so cut to 2 seeds, see 08.02 above).
Read at the sources for the pages, beyond what is above:
- Vaswani et al., the PDF of arXiv 1706.03762v7: section 3.1, the norm
  after the addition, LayerNorm(x + Sublayer(x)); 3.2.2, "Multi-head
  attention allows the model to jointly attend to information from
  different representation subspaces at different positions. With a
  single attention head, averaging inhibits this." and "Due to the
  reduced dimension of each head, the total computational cost is similar
  to that of single-head attention with full dimensionality."; 3.3,
  "applied to each position separately and identically", inner layer
  2048 for 512; 3.4, "we share the same weight matrix between the two
  embedding layers and the pre-softmax linear transformation"; 3.5, "The
  positional encodings have the same dimension d_model as the embeddings,
  so that the two can be summed." and the sentence on learned positions;
  5.3, Adam with warmup_steps = 4000, then the rate falls as one over the
  square root of the step; 5.4, Residual Dropout: "We apply dropout to the
  output of each sub-layer, before it is added to the sub-layer input and
  normalized. In addition, we apply dropout to the sums of the embeddings
  and the positional encodings in both the encoder and decoder stacks."
  (base rate 0.1); table 3 rows (A), (C) and (E) as quoted above, and row
  (D): dropout 0.0 5.77 / 24.6, 0.2 4.95 / 25.5, with "dropout is very
  helpful in avoiding over-fitting" under the table.
- Radford et al. (2019), section 2.3, in the PDF: "Layer normalization (Ba
  et al., 2016) was moved to the input of each sub-block, similar to a
  pre-activation residual network (He et al., 2016) and an additional
  layer normalization was added after the final self-attention block."
- Haviv et al. (2022), the paper itself now (arXiv 2203.16634v2, Findings
  of EMNLP 2022), not only its abstract: table 1, validation perplexity
  without positions against learned ones, 20.97 against 20.42 on
  WikiText-103 (a 247M model, 512 tokens) and 13.10 against 13.05 on the
  Pile (1.3B, 1024 tokens); table 2, 125M to 1.3B; section 5, shuffling
  the tokens before one token of a model without positions raises its
  loss "from ~4 to ~11"; section 6 and table 4, a masked language model
  without positions: perplexity 147.18 against 4.06 with learned ones
  ("training without positional encodings (NoPos) fails").
- Holtzman et al. (arXiv 1904.09751v2, ICLR 2020), in the PDF: table 1
  and figure 9's caption as quoted above; GPT-2 Large, 762M, 5,000
  passages of up to 200 tokens after 1 to 40 tokens of held-out WebText;
  temperature is their equation 4; section 3.1, "selecting the highest
  probability tokens whose cumulative probability mass exceeds the
  pre-chosen threshold p"; 4.2, "we argue that the optimal generation
  strategy should produce text which has a perplexity close to that of
  the gold text".
- nanoGPT's README: the Shakespeare character model, "a 6-layer
  Transformer with 6 heads in each layer", "a context size of up to 256
  characters, 384 feature channels", "the best validation loss is 1.4697"
  (nats; 2.120 bits, on its own split), about 3 minutes on one A100;
  model.py: the c_proj scaling by 0.02/math.sqrt(2 * config.n_layer), the
  decay groups by p.dim() >= 2, generate's temperature and top_k.
Not checked, so not on the pages: the content of Karpathy's video beyond
its description, and what chapter 5 of Raschka's book does with sampling.
The Break its, run on the project at each lesson (same machine):
- 08.01, `.tril(1)` in causal_mask (each position also sees the next
  character): "masked" last batch 2.34, test as trained 2.307, past only
  4.592 (worse than no mask), its text 300 newlines; part 3, one position
  changed, by 0.811; part 1's trained rows 4.592 and 4.277 (both leak).
- 08.02, both `x +` out of Block.forward: 1 block 3.639, 4 blocks 4.82 (t
  = +40.2), 4 blocks of 1 head 4.853; every head of blocks 2 to 4 at 11.1
  back.
- 08.03, Positions adding row 0 at every place: learned positions 3.416
  against none 3.407 (t = +1.0); order test 3.18; the last 32 before each
  3.430; block 1's heads near equal again.
- 08.04, load() without load_state_dict: "the same scores, number for
  number: False", and the text is equal chances (8 of its 500 characters
  are $).
- 08.05, top_p without "- chances": a RuntimeError from torch.multinomial
  at the nucleus (every score -inf where the likeliest has 0.95 or more).
  Tried first and not used: held_bits without eval(), which changes the
  training itself (dropout's draws move torch's generator: dropout 0.2
  test 3.458 instead of 3.474).
Seen while drawing: 08.01's trained head (seed 0, masked) puts 0.93 to 1
of a row's weight on its own position for most characters and splits it
evenly between equal characters (0.49 and 0.49 for two spaces, a third
each for three, the o of "ho" half on the o of "Not"): equal keys. 08.05's
small model after prompt 1 gives "t" 0.22, and its nucleus at 0.95 keeps
18 of the 65 characters.

### Module 09: GPT-2, the tokenizer and the real weights

New in the project: tokens/ (a package of its own, as models/ is; not
"tokenizers", which would hide the installed library of that name): bpe.py
(09.01) and gpt2.py (09.02); models/gpt2.py (09.03); data/tinystories.py
(09.04); experiments bpe, tokenizer, gpt2, tinystories; two shared
regions: experiments/sequences.py per_character (09.01: bits per token
made bits per character, used by 09.01, 09.03, 09.04) and
experiments/language.py loops (09.03: 08.05's repetition for any symbols,
used by 09.03 and 09.04; an experiment never imports another, so 08.05's
repeats in sampling.py could not be reused). data/fetch.py gains gpt2
(09.02) and tinystories (09.04) in @from blocks and fetch_each, a
resumable download of separate files or of a range of bytes of a larger
one. lab/safetensors.py's load_file reads in place from 09.03 (an @from
block inside the 02.05 region; 02.05 shows the old one). The learner's
code imports numpy, torch and the standard library only; tiktoken,
transformers and the regex module are used by the tests only.

**09.01 Bytes, UTF-8 and byte pair encoding (Sennrich, Haddow and Birch
2016).** tokens/bpe.py: pieces (the text cut by ` ?\w+| ?[^\w\s]+|\s+`, a
word with the space before it, a run of other marks with the space before
it, a run of spaces; every character is in exactly one), pairs, merge,
train_simple (the obvious trainer: every pair of every piece of the whole
text counted again for every merge), train (the same merges: each distinct
piece once with its count, and `where`, the pieces that hold each pair, so
a merge changes only those), encode (each piece's bytes, then the pair
learned first merged, again and again), vocab, decode (UTF-8, a cut
character U+FFFD). The rule for ties: of pairs counted equally often, the
smaller pair (first symbol, then second), so the merges do not depend on
the order the text is read in (the paper's Algorithm 1 takes
max(pairs, key=pairs.get), the first in dictionary order). Pairs never
cross pieces. experiments/bpe.py, default run:
1. The failure, counted on Tiny Shakespeare's own split (a word: a run of
   letters, [A-Za-z]+). Characters: 65 symbols, and 08.04's window of 256
   characters holds 47.7 words on average (38 to 55; 2000 windows of the
   test text drawn with rng 0). Words: the training text has 187,779
   words, 12,558 different; of the test text's 2,396 different words
   15.9% never occur in training, which is 6.9% of its 10,264 running
   words (lowercased: 13.1% and 5.8%; with apostrophes inside words,
   [A-Za-z]+(?:'[A-Za-z]+)*: 16.8% and 7.6%; spike, not printed). A model
   with one symbol for each training word could give none of those a
   chance.
2. The trainers, on the training text (1,003,854 bytes, 264,485 pieces,
   14,134 different). The obvious one: 0.45 to 0.69 s a merge (3 merges
   timed, load 5 to 12), so the default's 1,792 merges (a vocabulary of
   2048) would take about 16 minutes, and 3,840 (4096) 29 to 44. The fast
   one: 1,792 merges in 2.3 to 2.4 s (512: 0.4 s, 1024: 0.9, 4096: 6.0 to
   10.2 with the machine busier, 8192: 13.3); the run checks its first 3
   merges are the obvious one's, the test checks whole merge lists (below).
   This is the paper's own way: "For efficiency, we do not consider pairs
   that cross word boundaries. The algorithm can thus be run on the
   dictionary extracted from a text, with each word being weighted by its
   frequency", and "In practice, we increase efficiency by indexing all
   pairs, and updating data structures incrementally" (section 3.2, read
   at the source, arXiv 1508.07909v5). The first symbols made: ' t' 'he'
   ' a' 'ou' ' s' ' m' 'in' ' w' 're' 'ha' ' the' 'nd' ' b' 'is' 'or'
   '\n\n' ...; the last of 2048: ' dish' ' gates' 'oop' ' stir' ...
   ' heavens' ' close' ' harm'; of 4096 ' hanging' ' services' ...
   ' possible'; at 8192 the last ones are names of the training plays
   (' Chertsey', ' Crosby').
3. Bytes per token (training text / test text): 256: 1.000 / 1.000; 512:
   1.957 / 1.890; 1024: 2.458 / 2.268; 2048: 2.916 / 2.579 (the default
   stops there); 4096: 3.291 / 2.916 (`"sizes=[256,512,1024,2048,4096]"`,
   the first default, 38.7 s at load 5.5 to 5.9, 60.8 s at load 8 to 11);
   8192 (spike): 3.567 / 3.176. The gap grows with the vocabulary: the
   later merges are the training text's own words.
4. Round trips with the vocabulary of 2048: the test text (21,627 tokens;
   19,127 at 4096)
   and eight strings the training text never had (accents, Greek,
   Russian, Chinese, Hindi, an emoji with a skin tone and a flag, a
   combining accent, a tab, a NUL and a DEL; escapes in the file): all
   decode to themselves. Greek's 16 bytes are 16 tokens (no merge has its
   bytes); "na\xefve caf\xe9, se\xf1or" 20 bytes, 14 tokens.
5. 08.04's GPT (4 blocks of 4 heads, width 64, windows of 64 symbols, 300
   steps of 32, AdamW 0.003, the same seeds) on characters and on BPE
   tokens of 2048, both in bits per character on the test text (each
   token scored with 16 or more before it; the bits of the scored tokens
   over the characters they stand for: per_character): characters `3.332
   +- 0.01587` (08.04's default dropout 0 to the last digit: the same
   model, data and draws), BPE 2048 `2.691 +- 0.00954`, t = -49.0. A step
   reads 2,048 characters on characters and 5,973 on tokens, and the
   window of 64 tokens is about 187 characters: at equal steps the
   tokens see 2.9 times the text. Spike (300 steps, 2 seeds, load 4 to
   5): 512 2.865 / 2.869, 1024 2.802 / 2.813, 2048 2.698 / 2.684. As
   found: the bigger the vocabulary the lower, at this budget; at equal
   characters read, not measured. With 200 steps (spike, load 10 to 12):
   characters 3.473, BPE 2.787, t = -91.1.
41.1 s at load 7 to 10 (10 threads; other agents' runs); 37.8 s at load 4
to 5. The same digits each time.

**09.02 GPT-2's tokenizer: the same ids as tiktoken (Radford et al.
2019, section 2.2).** tokens/gpt2.py: byte_symbols (GPT-2's table of the
256 bytes as printable characters: "!" to "~", 0xa1 to 0xac and 0xae to
0xff as themselves, the other 68 as chr(256 + n) in byte order: a space
is U+0120, a newline U+010A), classes, pattern, split, Tokenizer (table,
first, merges; encode with a cache of pieces; decode is 09.01's), load.
GPT-2's files are 09.01's form exactly: vocab.json's ids for the merged
symbols are 256 + the line of merges.txt (checked by Tokenizer: a file
out of order is a ValueError), so the merges become {(id, id): new id}
and 09.01's merge loop (smallest new id first) gives OpenAI's ids. The
byte symbols' ids are not their bytes ("!" is 0), hence `first`.
The pattern without the regex module: GPT-2's own pattern (OpenAI's
encoder.py, `import regex as re`), `'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+|
?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+`, with \p{L} and \p{N} replaced
by character classes built from unicodedata (every code point whose
category starts with L, or N, written as runs of ranges with \U escapes:
136,104 letters in 1,181 runs, 1,831 numbers in 268 runs; 0.07 s, made
once), and \s by Unicode's White_Space, written out (SPACE: 25 code
points; unicodedata does not have the property). re's own \s is
str.isspace(), which has four more, 0x1c to 0x1f (the information
separators); the regex module's \s is exactly SPACE (checked over every
code point). No merge in GPT-2's file has those four bytes, so re's \s
would give the same ids, but other pieces (split("x \x1c y") is "x", "
\x1c", " y" with SPACE). Every other part of the pattern is re's own:
alternation tried in order, backtracking into \s+ for (?!\S). tiktoken's
r50k pattern is written differently ('(?:[sdmt]|ll|ve|re)| ?\p{L}++|
... |\s++$|\s+(?!\S)|\s) and cuts the same.
experiments/tokenizer.py, default run (needs `python3 -m data.fetch gpt2`):
1. The files: 50,257 symbols, 50,000 merges, 50256 is <|endoftext|>; the
   first merges ' '+'t', ' '+'a', 'h'+'e', 'i'+'n', 'r'+'e', 'o'+'n', ' t'+'he'
   ...; the longest symbol, 35496, is 128 bytes (the mojibake "\xc3\x83\xc3\x82"
   32 times: web pages decoded twice), then runs of "=" "-" "." "_".
2. The pieces of "Hello world! It's 2019, isn't it?  Yes...\n\n   NAME:\tna\xefve
   3.14 caf\xe9s": GPT-2's 'Hello' ' world' '!' ' It' "'s" ' 2019' ',' ' isn' "'t"
   ' it' '?' ' ' ' Yes' '...' '\n\n  ' ' NAME' ':' '\t' 'na\xefve' ' 3' '.' '14'
   ' caf\xe9s' against 09.01's re pattern (\w lumps letters, digits and _;
   no contractions; spaces not left for the next word).
3. "Hello world" [15496, 995]; " SolidGoldMagikarp" [43453], one token;
   "1234567890" '123' '45' '678' '90'; "IT'S" 'IT' "'" 'S' (the
   contractions are lower case only); U+4F60 U+597D ("hello" in Chinese) 4 tokens of byte
   pieces; the waving hand with a skin tone 5. All of Tiny Shakespeare,
   1,115,394 bytes, is 338,025 tokens, decoded the same.
4. Bytes per token on Tiny Shakespeare, GPT-2 (50,257, learned on WebText)
   against 09.01's 4,096 learned on the training text: training text 3.324
   against 3.291, test text 3.099 against 2.916 (validation, GPT-2: 3.087).
   Twelve times the vocabulary buys 1% on the text 09.01's merges were
   learned on and 6% on the test text: GPT-2's merges were not learned on
   Shakespeare.
5. Encoding all of Tiny Shakespeare (1.12 MB), best of 2: without the
   cache 0.90 to 0.91 s (1.23 MB a second), with it 0.24 s (4.7 MB a
   second); 297,833 pieces, 15,057 different. tiktoken (Rust) 0.043 s
   (26 MB a second), transformers' fast tokenizer 0.28 s, its slow
   (Python, regex module) 0.78 s; the regex classes 0.07 s and reading
   the files 0.06 s once.
8.4 s at load 1.5 to 2.7, 8.7 s at load 5, 15.0 s at load 10 to 11 (most of
it 09.01's trainer to 4096 for part 4).
The same ids as the references: the test compares with every reference
it can import, each built from the fetched files (no network: tiktoken's
Encoding from tiktoken.load.data_gym_to_mergeable_bpe_ranks on the local
merges.txt and vocab.json, with tiktoken's own r50k pattern;
transformers' GPT2TokenizerFast and, when the regex module imports,
GPT2Tokenizer from the same two files) and prints which: here tiktoken
0.14.0 (installed for the test with `python3 -m pip install --user
tiktoken`), transformers 4.57.6 GPT2TokenizerFast (tokenizers 0.22.2) and
GPT2Tokenizer (regex 2026.2.28). The corpus: all of Tiny Shakespeare (one
string), built strings (runs of 1 to 12 spaces and 1 to 5 newlines and
their mixes with words, contractions in every case and odd places,
digits of several scripts and Roman numerals, punctuation runs,
combining marks, Hangul jamo, 18 scripts, emoji with skin tones, ZWJ
families, flags and keycaps, and their mixes), 3000 random strings drawn
from up to 40 characters of every general category unicodedata knows
(assigned ones, and unassigned ones from planes 4 to 13, which no Unicode
version has assigned yet), and every such character in 8 contexts ("x{}",
"{}x", " {}", "{}'s", "1{}", "{}1", "'{}", " {}!"). Every id equal to all
three references; every string decodes to itself; split equals the regex
module running GPT-2's own pattern on the built and the random strings.
Where ids differ, and why (found, not designed): Python 3.12.7's
unicodedata is Unicode 15.0.0. tiktoken 0.14.0 and tokenizers 0.22.2
classify letters and numbers by Unicode 16.0, the regex module 2026.2.28
by 17.0. A character assigned since 15.0 is a letter or a number to them
and unassigned ("other") here. That changes ids only where the piece
boundary meets a merge: before a contraction. U+1C89 followed by "'s" (U+1C89 is a
Cyrillic capital letter added in 16.0) is cut U+1C89 + "'", "s" here, ids
[157, 110, 231, 6, 82], and U+1C89, "'s" by tiktoken, [157, 110, 231,
338]. Scanned: of the 104,782 code points unassigned in 15.0 in planes 0
to 3, each before "'s", 5,004 give other ids than tiktoken and the fast
tokenizer, U+1C89 to U+2EE5D, and 9,661 other ids than the slow one,
U+088F to U+33479; in every one the reference's ids are ours for the
character alone followed by ours for "'s" (the test asserts this). 5,004
is exactly the letters and numbers Unicode 15.1 and 16.0 added (counted
with Python 3.14.6's unicodedata, Unicode 16.0.0: 622 from 15.1, CJK
Extension I, the rest 16.0's); 9,661 adds 17.0's 4,657. With Python 3.14
the ids should equal tiktoken's on all of them (not run: the project's
python is 3.12). In any other context the pieces differ but the ids do
not (no merge joins those bytes to their neighbours), e.g. "x" + c, " "
+ c, "1" + c for all 9,661.

**09.03 Loading GPT-2: the same logits as the reference.** models/gpt2.py:
CONFIG (GPT(vocab=50257, context=1024, layers=12, heads=12, width=768,
dropout=0.0, bias=True, positions=True)), from_gpt2 (the mapping of "For
module 09 and after" below as code, on numpy arrays: transposed views,
no copies) and load(dev, path). lab/safetensors.py's load_file, as
written in 02.05, read the whole file into bytes, copied the data part
into a bytearray, and copied each tensor out of it: measured on GPT-2's
548 MB, a peak of 2,127 MB (ru_maxrss) to hold 523 MB of arrays, four
times the file. From 09.03 (an @from block inside the 02.05 region, the
old code its @else) it reads the header, checks every range before
reading anything, then reads each tensor straight into its own array
(np.fromfile on the open file, in offset order): peak 559 MB, 0.06 s
from the page cache; the same arrays as the safetensors library's (every
tensor, dtype and value), writable; 02.05's test passes unchanged, and
09.03's test holds it at under 1.3 times a 96 MB file in a fresh python
(measured 1.0). Loading GPT-2 whole (load_file, from_gpt2, GPT(**CONFIG)
with its random start, load_state_dict): 1.3 s, peak 1,197 MB.
The reference: transformers 4.57.6 GPT2LMHeadModel.from_pretrained on a
folder with GPT2Config() (the defaults are GPT-2 small) and a link to
the same model.safetensors, local_files_only (no network),
attn_implementation="eager". Logits on 1,024 tokens of Tiny Shakespeare
and on 4 rows of 64 random tokens: identical, the largest difference 0.0
in float32 (logits up to 342), and 0.0 in float64 too (both models
.double()). Same operations in the same order: transformers' Conv1D is
addmm(bias, x, W) on the file's (inputs, outputs) weight, nn.Linear
addmm with the transposed view of ours, the same GELU formula, the same
softmax of the same masked scores. With transformers' default attention
(sdpa) the largest difference is 4.1e-3 (relative to 1 + |logit|,
1.2e-3). The test asserts eager at 1e-4 of (1 + |logit|) in float32, and
prints the largest difference. Without the transpose of attn.c_proj (a
square 768 x 768 weight in each block): load_state_dict takes it without
a word, the largest difference from the reference is 111 to 323 and the
top token agrees at 7.6% of positions; a non-square weight left
untransposed is refused (size mismatch).
experiments/gpt2.py, default run:
1. GPT-2: after "The meaning of life is" ' not' 0.109, ' to' 0.083, ' the'
   0.051, ' that' 0.048, ' a' 0.040; greedy after "Hello, I'm a language
   model," gives " not a programming language. I'm a language model. I'm
   a language model. I'm a".
2. attn.c_proj untransposed: on the first 1,986 test tokens 3.493 bits
   per character against 1.814 right.
3. Tiny Shakespeare's test text: 55,770 characters, 17,995 GPT-2 tokens
   (3.10 characters a token); each token with 64 or more before it,
   windows of 1024: 5.737 bits per token, 1.851 bits per character
   (warm 256: 1.816; warm 512: 1.806; spike). Beside the ladder: equal
   chances 6.022, pairs 3.599, interpolation 2.409, 07.02's network
   2.346, mixed 2.283, 08.04's GPT 2.226. GPT-2 is 0.375 bits per
   character below 08.04's best. Not "never seen": WebText is 8 million
   web pages (Wikipedia removed, section 2.1); some may hold
   Shakespeare. What can be said: we did not train it on this text.
   Comparability: GPT-2 reads 64 tokens (about 200 characters) before
   the first scored one, our models 64 characters.
4. 08.05's measurements on the real model, on word pieces: 8 prompts of
   16 tokens (starts of speeches of the test text, evenly spread), 40
   tokens after each, 2 seeds of the sampling (greedy once), the model's
   perplexity per token of what it wrote (prompt and continuation in one
   window: perplexity, a 09.03 region) and Holtzman et al.'s repetition on
   tokens (loops, 08.05's measure moved to language.py). Default run:

       the text itself    64.74                                         0.0%
       greedy             2.386 (no chance in it)                      50.0%
       pure sampling      48 +- 3.397 (min 45.6, max 50.41, 2 seeds)    0.0%
       sampling, t=0.9    26.58 +- 6.273                                0.0%
       sampling, t=0.7    10.49 +- 3.395                                0.0%
       top-k=40           13.01 +- 1.933                                0.0%
       nucleus, p=0.95    34.14 +- 6.406                                0.0%

   With prompts of 32 tokens (the first default, cut for time: 42.3 s at
   load 2.6 but 81.7 s at load 12): text 65.9, greedy 2.311 and 37.5%,
   pure sampling 38.83, t=0.9 22.38, t=0.7 7.63, top-k=40 11.13, nucleus
   29.4; the same picture.
   A longer run, closer to the paper's set-up (prompt_tokens=32 prompts=16
   length=200 seeds=3; 32 minutes at load 3 to 15, not a default):

       the text itself    53.87                                         0.0%
       greedy             1.202 (no chance in it)                     100.0%
       pure sampling      71.94 +- 12.11 (min 61, max 84.95, 3 seeds)   0.0%
       sampling, t=0.9    23.12 +- 0.693                                0.0%
       sampling, t=0.7    3.602 +- 0.3526                              20.8% (25, 12, 25)
       top-k=40           9.552 +- 0.7457                               0.0%
       nucleus, p=0.95    37.31 +- 4.076                                0.0%

   Against the paper's table 1 (GPT-2 Large, WebText, 200 word pieces;
   quoted in 08.05's notes: human 12.38 / 0.28%, greedy 1.50 / 73.66%,
   pure 22.73 / 0.22%, t=0.9 10.25 / 0.66%, top-k=40 6.88 / 0.78%,
   top-k=40 t=0.7 3.48 / 8.86%, nucleus 0.95 13.13 / 0.36%). Held, on the
   real model: greedy degenerates (perplexity 1.2, every passage of 200
   ends in a loop; at 40 tokens 2.4 and 4 of 8 already loop: "Pitchers
   have ears, and I have many ears." over and over); at 200 tokens pure
   sampling's text is less likely to the model than the text itself (72
   against 54, 34% above; the paper's 84% above): "the model is confusing
   itself", which 08.05's character models never showed; a temperature
   of 0.7 brings loops back (21%; the paper's figure 9). Did not hold: the
   nucleus is not the closest to the text: at 200 tokens it lies below
   the text (37 against 54) about as far as pure sampling lies above it.
   And at 40 tokens pure sampling is below the text (48 against 65): just
   after a Shakespeare prompt the model's own words are likelier to it
   than Shakespeare's next ones; over 200 tokens it wanders off into web
   prose (the passages above: "the American I have in my upper depths",
   "Squad Volunteers") and loses itself. The text is the other difference:
   the paper's human text was held-out WebText (perplexity 12.38 to GPT-2
   Large), ours Shakespeare (54 to 66 to GPT-2 small). The default shows
   greedy's loops and the temperature's pull; the claim about pure
   sampling needs the longer run, and the page should quote it.
42.8 s at load 8 to 10 (10 threads; other agents' runs); 44.4 s at load 5;
the same output each time. The slowest default of the module: GPT-2's
forward is a big matrix product on 10 threads, so a busy machine slows
it most (81.7 s at load 12 with the first default's prompts of 32
tokens). If verify sees it pass 55 s, cut length to 32 or prompts to 6
(not measured).

**09.04 Pretraining on TinyStories (Eldan and Li 2023).**
data/tinystories.py: stories (the file cut at each <|endoftext|>, the
training range's last cut piece dropped, stripped, empty ones left out;
28 empty ones in 128 MB of the file), tokenizer (09.01's train on the
first 10,000 training stories, one to a line; 3,839 merges in 5.0 s; kept
as JSON), tokens (every piece merged once, remembered, END after each
story; 2.9 s for 64 MiB, 1.0 s for valid; kept as .npy). The first
merges: 'he' ' t' ' a' ' s' ' w' 'nd' ' the' 'ed' ' and' 'in' ' to'
...; the last: ' sheep' ' switch' ' celebrated' ' Chloe' ' classroom'
' impressive'. experiments/tinystories.py: tell (generate in chunks of
32 tokens, stopped once every story has written END; a story is its
tokens before END), kgram_hashes and shared_run (copying: see below),
copying and measure (not regions).
Spike 4, what I tried (the plan left the size, vocabulary and steps to
it). The CPU budget: 2 seeds in at most 60 minutes, so about 25 minutes
a seed. Speeds measured on the CPU (10 threads, load 7 to 8, windows of
256, batches of 32, vocabulary 4096): 4 x 128 (1.35M weights) 195 ms a
step, 6 x 192 (3.5M) 464, 4 x 256 (4.27M) 430, 6 x 256 (5.9M) 630, 8 x
256 (7.4M) 809; at load 6: 4 x 256 288 ms, 4 x 128 136 ms. Each candidate
was then trained on the Apple GPU (mps, 3 times faster; 1 seed) for the
steps the CPU makes in about 27 minutes, and scored the same way (bits
per byte on the first 2000 held-out stories; 16 stories at temperature
1, up to 600 tokens):
- 4 blocks of 4 heads, width 128 (1,350,400 weights), 9500 steps, lr
  0.002: 0.7348 bits per byte; held-out windows 2.978 bits per token at
  the end; 16 of 16 stories ended on their own, median 204 tokens, none
  in a loop.
- 6 x 192, 6 heads (3,505,152), 4000 steps, lr 0.001: 0.7564; 3.056;
  16 of 16, median 194, none.
- 4 x 256, 8 heads (4,273,664), 4400 steps, lr 0.001: 0.7267; 2.940;
  16 of 16, median 202, none.
All three tell whole stories at this budget, with "Once upon a time",
names kept, dialogue in quotes, an ending ("From that day on, ...", "The
end."), and sentences that do not follow from each other; the three
are within 0.03 bits per byte. Chosen: 4 x 256, 8 heads, the best and "a
few million weights" (the paper's "below 10 million"), at 4000 steps
(not 4400, for room under the hour at a busier machine's 0.43 s a step).
Vocabulary 4096 (4,095 symbols and END): 3.95 bytes a token on both
files (2048: 3.66 on valid; spike); the paper kept GPT-Neo's top 10,000
tokens. Windows of 256 hold 80% of stories whole. Not tried: other
learning rates for 4 x 256, dropout (the data is not repeated much: 2
passes in the long run), windows of 512.
Measured for the lesson, what code can check (the paper's grading by
GPT-4 is not run): bits per byte on held-out stories (the first 2000 of
the validation file in the long run, 200 in the default; END counted as
one byte, the line it stands for); whether a story ends on its own (the
model writes END within `length` tokens); its length in tokens and
words; repetition (loops, 08.05's: a phrase of 2 or more tokens 3 times
at the end); copying: the longest run of tokens a story shares with the
training tokens (16.7 million), found with an index of every run of 8
(hashes sorted, 3 s) and followed token by token; runs under 8 count 0;
beside the same for held-out stories, which no model saw. The paper
measured copying another way (Rouge-k precision against the training
set and the share of k-grams that occur in it, its section 4.4); the
longest shared run is a simpler check of the same thing.
Reference point (spike, 210 s): GPT-2 small (124M, WebText, its own
tokenizer, 4.16 bytes a token) on the first 2000 held-out stories: 0.836
bits per byte (3.477 bits per token, windows of 1024, warm 64).

The default run (no checkpoint; in verify's copy of the project there is
none): 4 blocks of 4 heads, width 128, windows of 128 tokens (1,334,016
weights), 120 steps of 32 windows (491,520 tokens, 0.03 passes), AdamW
0.003, warmup 20, 2 seeds. Bits per byte on the first 200 held-out
stories `1.571 +- 0.08948` (min 1.507, max 1.634). Its stories (seed 0,
8 at temperature 1, at most 300 tokens): 4 of 8 end on their own, none
in a loop, 8 to 245 words, no run of 8 tokens shared with the training
text: story-shaped words without sense ("Once upon bad secret became
swing does a very squirrel cried. / Lily was very bowance."). The first
8 held-out stories share runs of 11, 13, 13, 17, 11, 16, 14, 19 tokens
(9 to 17 words) with the training text, the longest "Once upon a time,
there was a little boy named Tom. He loved to play with his": the
stories' own formulas. 21.9 s at load 7; 24.1 s at load 5 to 6; 28.2 s at
load 10 to 12 (the
tokens read from the cache; making them first adds about 9 s). With the
long run's checkpoint in experiments/recorded/tinystories/ (a learner who
ran it again) the same run measures it too: 45.0 s at load 9 to 12; on
the first 200 held-out stories 0.6266 bits per byte (the first 200 are
easier than the first 2000: 0.7358, below), 7 of 8 stories end within
300 tokens, 61 to 230 words, shared runs 9 to 19 tokens.
The long run, recorded in experiments/recorded/tinystories/ (config.json,
log.jsonl and summary.json of each seed; stories-trained-here/ and
stories-held-out/, the measures as summary.json; curves.svg, the
held-out windows' bits per token; output.txt, what it printed, all 16
stories with it, two curly quotes printed as escapes). Its checkpoint
(model.safetensors, 17.1 MB) was moved out: no weights are shipped.

    python3 -m experiments.tinystories layers=4 heads=8 width=256 context=256 batch=32 steps=4000 lr=0.001 warmup=100 every=250 seeds=2 held=64 held_stories=2000 samples=16 length=600 shown=16 checkpoint=none out=experiments/recorded

4 blocks of 8 heads, width 256, windows of 256 tokens, 4,273,664
weights; 4000 steps of 32 windows (32,768,000 tokens, 1.96 passes over
the 64 MiB), AdamW 0.001, weight decay 0.1, warmup 100 then cosine, no
dropout; 2 seeds. 2702 s by its own clock, 45 min 3 s of wall clock
(20:43:21 to 21:28:24), 10 threads, load 6 to 14 (other agents' runs; four
of module 14's from 21:20 slowed the last minutes): seed 0 in 20 min
(0.30 s a step), seed 1 in 23.
- Bits per byte on the first 2,000 held-out stories: `0.7367 +- 0.001263`
  (0.7358, 0.7376). The held-out windows (64) end at 2.978 and 2.974 bits
  per token, still falling slowly at the end (2.980 and 2.976 at step
  3750): nothing turns up in 2 passes. The same model on the GPU for 4400
  steps (spike): 0.7267. GPT-2 small (124M, WebText, its own tokenizer)
  on the same 2,000 stories: 0.836 (spike, above): a model 29 times
  smaller, trained 45 CPU minutes on the right text, predicts these
  stories better than GPT-2 small.
- Stories (seed 0, the better; 16 at temperature 1, at most 600 tokens):
  16 of 16 end on their own (END), none in a loop, 102 to 323 words
  (median 172). Copying: the longest run of tokens each shares with the
  training text 19, 11, 9, 11, 14, 10, 10, 14, 12, 15, 8, 12, 0, 14, 10,
  19 (median 11.5; 0 to 17 words), against 11 to 23 (median 14; 9 to 19
  words) for the first 16 held-out stories, which no model saw. The
  model's stories share shorter runs than real unseen stories do: no
  sign of copying beyond the formulas ("Once upon a time, there was a
  little girl named Lily. Lily was very happy because she", 19 tokens).
- What they read like (output.txt has all 16): "Once upon a time, there
  was a happy little rabbit named Timmy. Timmy loved to run and jump in
  the air. One day, Timmy saw a cherry was still singing a song. He
  picked it up and showed it to his friend, a little girl named Lily. /
  "Hi Timmy! Can you help me get a cherry cherries from the bin?" said
  Lily. / Timmy thought for a moment and then said, "Yes, I like
  cherries." / Lily chose lots of cherries too and they agreed together.
  They ate fruits and passed hours. At the end of the day, they paid for
  the cherry tree, and Timmy became very popular with his friend." Whole
  stories in paragraphs, a beginning, dialogue in quotes, an ending ("The
  end.", "From that day on", a moral), most clauses grammatical; names
  drift (Flanna, Flongoantly, Marna in one story), made words appear
  ("membori", "pallengenty"), and one sentence rarely follows from the
  last.
Against the paper. Eldan and Li's claim (abstract, read at the source,
arXiv 2305.07759v2): TinyStories "can be used to train and evaluate LMs
that are much smaller than the state-of-the-art models (below 10 million
total parameters) ... yet still produce fluent and consistent stories
with several paragraphs that are diverse and have almost perfect grammar,
and demonstrate reasoning capabilities". Held at laptop size: a model of
4.3 million weights writes whole stories of several paragraphs that end
on their own, in the dataset's form, without copying its training text.
Not held: consistent, and almost perfect grammar; their models were
trained "on a single V100 GPU within at most 30 hours" (section 4) on all
of TinyStories (1.9 GB; ours 64 MiB, 2 passes, 45 CPU minutes), and
graded by GPT-4 (not run here). Their figure 4's evaluation losses
(about 1.3 to 2.3) are per token of GPT-Neo's tokenizer (its top 10,000
tokens), not comparable with bits per byte here. Their models "learn when
to stop generating correctly" (figure 4's caption): ours do too (16 of
16).

**Module 09's papers: what was read at the source.** On 2026-11-24, from
the papers themselves:
- Sennrich, Haddow and Birch, arXiv 1508.07909v5 (ACL 2016): section 3.2
  (the quotes in 09.01), Algorithm 1 (`best = max(pairs, key=pairs.get)`:
  ties go to the pair counted first), the end-of-word symbol (their BPE
  is on characters with a mark at each word's end; ours on GPT-2's bytes,
  where the space starts a word instead), "The final symbol vocabulary
  size is equal to the size of the initial vocabulary, plus the number of
  merge operations", footnote 3 (only unknown characters can be unknown:
  with bytes, none). Their translation experiments are not run.
- Radford et al. 2019 (the PDF at cdn.openai.com/better-language-models/):
  section 2.2, "We observed BPE including many versions of common words
  like dog since they occur in many variations such as dog. dog! dog? ...
  To avoid this, we prevent BPE from merging across character categories
  for any byte sequence. We add an exception for spaces which
  significantly improves the compression efficiency"; Unicode code points
  "would result in a base vocabulary of over 130,000 before any
  multi-symbol tokens are added", "a byte-level version of BPE only
  requires a base vocabulary of size 256" (09.02: 136,104 letters alone
  in Unicode 15.0); section 2.3, "The vocabulary is expanded to 50,257. We
  also increase the context size from 512 to 1024 tokens"; table 2 gives
  the smallest model as 117M parameters, where its published file holds
  124,439,808 (the paper does not say how it counted); section 2.1,
  WebText is "slightly over 8 million documents for a total of 40 GB of
  text", Wikipedia removed. OpenAI's src/encoder.py (github, master):
  `import regex as re` and the pattern of 09.02, word for word.
- Holtzman et al. 2020: 08.05's notes have the quotes (read there).
- Eldan and Li, arXiv 2305.07759v2: the abstract (quoted in 09.04);
  footnote 2, "We use GPT-Neo architecture with window size 256 and
  context length 512. We use GPT-Neo tokenizer but only keep the top 10K
  most common tokens"; section 4, "All of the models can be trained on a
  single V100 GPU within at most 30 hours"; figure 4 (evaluation losses
  and GPT-4 grades by hidden size and layers, and its caption: "our
  models learn when to stop generating correctly"); section 4.4 (copying
  measured by Rouge-k against the training set). Not found in the pages
  read: their learning rates, batch sizes and step counts.
Departures from the design, and why (each said above where it belongs):
09.01's default stops at a vocabulary of 2048 and 09.03's prompts are 16
tokens (time, on a busy machine); Holtzman's pure-sampling claim shows
only in 09.03's longer, unrecorded run (32 minutes); copying is measured
in tokens (each run's words beside it), not words; one fetch, gpt2, holds
the tokenizer's files and the weights, so 09.02 asks for all 549 MB;
TinyStories is the paper's own training file (GPT-3.5 and GPT-4), not
V2; load_file changed from 09.03 (it held the file four times); the
tests compare with tiktoken built from the fetched files
(tiktoken.get_encoding("gpt2") would download them); per_character and
loops are in the shared files, not in an experiment.

**Module 09's pages (lessons agent, 2026-11-24).** Four lessons and the
module page in lessons/09-gpt-2/; 18 figures from art/research/figs09.py
(the page's four runs; bpe.py again with sizes to 8192 for 09.01-sizes;
tokens/bpe.py, tokens/gpt2.py, models/gpt2.py and lab/safetensors.py run in
the project at each lesson; GPT-2's files, TinyStories' kept tokens, and
experiments/recorded/tinystories/; tiktoken for 09.02-unicode; each stops
if what it computes differs from what the page's run printed); the cover
from the track's own tokens/bpe.py and the recorded run, its numbers
asserted. What the pages say beyond the notes above, all measured or read:
- Read at the source for the pages: Sennrich et al.'s abstract ("making
  the NMT model capable of open-vocabulary translation by encoding rare
  and unknown words as sequences of subword units"; arXiv's comments line:
  "accepted at ACL 2016"); their section 3.2 opens "Byte Pair Encoding
  (BPE) (Gage, 1994) is a simple data compression technique" (the HTML of
  v5). RFC 3629, section 3: the four byte patterns, "sequences of 1 to 4
  octets". Eldan and Li's abstract: "a synthetic dataset of short stories
  that only contain words that a typical 3 to 4-year-olds usually
  understand"; section 2 "Description of the TinyStories dataset" (about
  1,500 basic words, chosen features per story), section 3 "GPT-Eval",
  where GPT-4 grades "grammar, creativity, and its consistency with the
  beginning of the story", section 4.4 "Diversity of the content
  generated by the model" with 4.4.1 on Rouge. OpenAI's src/encoder.py:
  bytes_to_unicode, whose docstring says it "avoids mapping to
  whitespace/control characters the bpe code barfs on", the pattern, a
  cache; src/model.py: conv1d with w of shape [1, nx, nf] and tf.matmul,
  gelu with tanh and 0.044715. tiktoken's README: "a fast BPE tokeniser for
  use with OpenAI's models". minbpe's README: the regex split "was
  introduced in the GPT-2 paper". The GPT-2 model card: "124M parameters".
  CS336's first assignment: "Implement all of the components (tokenizer,
  model architecture, optimizer) necessary to train a standard Transformer
  language model". Not checked: the YouTube pages gave only their titles.
- U+1C89 in a newer Python: python3.14 (3.14.6) is on this machine; its
  unicodedata is 16.0.0 and calls U+1C89 Lu, CYRILLIC CAPITAL LETTER TJE.
  09.02-unicode prints that; the project's own python is 3.12.7 (15.0.0).
  Recomputed for the figure with tiktoken 0.14.0: of the 104,782 code
  points Cn in planes 0 to 3, 5,004 differ before 's (U+1C89 to U+2EE5D),
  each as the character alone then 's; in 7 other contexts (x+c, c+x,
  space+c, 1+c, c+1, '+c, space+c+!) none of the 5,004 differs.
- Units of load_file's peak (09.03 above): 2,127 and 559 are MiB
  (ru_maxrss / 2^20). In millions of bytes, as the figure gives them: 2,214
  to 2,231 MB (two measurements) and 586 MB, the arrays 548 MB (37 MB
  before reading, python and numpy). The page says "over two gigabytes,
  four times the file".
- Break its, each run on the project at its lesson: 09.01, encode with
  ord(c) for the bytes: the test text still True; 'na\xefve ...' 11 tokens,
  False; Greek 8 tokens, False (954 is merge 699's symbol); Russian 6,
  False; the Chinese string stops with KeyError: 20320. 09.02,
  self.first = list(range(256)): "Hello world" [72, 101, ...], Tiny
  Shakespeare 1,088,538 tokens, decoded the same False, bytes per token
  1.024 and 1.031. 09.03, ("key", "query", "value") in from_gpt2: 3.943
  bits per character (12.219 per token), the text's perplexity 3591, after
  "The meaning of life is" ' the' 0.024, greedy ", the, the". 09.04, END
  taken out of the training tokens (train_np[train_np != end]): 16,635,183
  tokens, 1.569 +- 0.008076 bits per byte, 0 of 8 stories end within 300.
- 09.03's default took 59 s at load 11 to 14 while these pages were
  written (60 s through ./learn run); the planner's rule cuts it only at
  over 55 s with the load under 6, which was not seen: not cut.
- track.py's TOOLS gains "tiktoken" (installed or not), for 09.02's
  session that compares the ids with tiktoken's built from the fetched
  files; without tiktoken that lesson is "missing", not failed.

## For module 08: what module 07 leaves ready

- The text: `from data import shakespeare`; `shakespeare.split("train")`
  (numpy int64), `chars()`, `encode`, `decode`. Choose on "val", report on
  "test" (Data above: test is The Tempest, 0.2 bits harder).
- Batches: `experiments.sequences.windows(ids, starts, length)` gives x and
  the next symbol at every position, y, both (B, length): for a GPT draw
  the starts from run.rng (`torch.from_numpy(run.rng.integers(0, len(ids)
  - length - 1, B)).to(dev)`); 07.03 uses consecutive starts instead.
- Scoring: `window_bits(predict, ids, span, warm)`, bits per character over
  every test position from warm on, each with at least `warm` characters
  before it in its window; the window is warm - 1 + span long, so with a
  block of 256 take warm=64, span=193 and the GPT's numbers sit beside
  07.03's (warm=64). predict is the model itself for a GPT (scores (B, T,
  V)); `lambda x: model(x)[0]` for 07.03's RNN. `bits(scores, targets)` is
  the cross-entropy in bits for training losses.
- Sampling: `sample(next_scores, prompt, n, generator, temperature)`, a
  seeded torch.Generator; next_scores is given every number so far, so a
  GPT's is `lambda ids: model(ids[None, -block:].to(dev))[0, -1]`. Top-k
  and top-p (08.05) need no change to it: each is a function of the scores
  (the rest set to -inf), wrapped around next_scores.
- Attention: `from models.attention import attend`: self-attention is
  attend(q @ k.transpose(-2, -1) / sqrt(d) with the future masked to -inf,
  v): the mask goes on the scores before attend, which has no mask argument
  and needs none.
- 07's ladder, test bits per character, for 08.04 to print beside its GPT
  (recompute the counts with models.ngram, a few seconds; quote the
  networks): equal chances 6.022; single characters 4.850; pairs (add-k
  0.1) 3.599; best add-k (context 4) 2.629; deleted interpolation up to 7
  2.409; 07.02's network at 5 characters 2.474 (short run) and 2.346 (long
  run), mixed with interpolation 2.294 (long, 5) and 2.283 (long, 8);
  07.03's RNN 2.540 (short run, 600 steps; 800 steps 2.487; 5000 steps, 1
  seed, 2.375 as its page runs it with the committed code, where an earlier
  spike printed 2.369).
- Shared loops: module 07 has none like images.train_epoch (each script's
  train is its own: random positions, streams, or tasks); 08 may write one
  in sequences.py or its own file, never in an experiment.
- Threads: unlike 06's ResNet-8 ("Seeds and determinism" above), 07.02's
  network gives other bytes with 1 thread than with 10 (the printed digits
  agree): a byte-for-byte test compares two runs on the same machine with
  the same thread count, as the tests here do. And with the machine busy
  (load 9 to 14 here), 10 threads were up to twice as slow as 4 for these
  small layers, with as much system time as user time: time a page's runs
  on a quiet machine, and say what was running.
- The models/ docstring (06.02) said every model after convnet imports
  torch, and models/ngram.py (07.02) is numpy only. Its last sentence is now
  a `# @from 07.02` block with an `# @else` part (as data/fetch.py's
  docstring has one for 06.03): before 07.02 it reads as it did, from 07.02
  on it says the count models of ngram.py are not networks and that file is
  numpy only. A module 08 that adds a numpy-only model keeps it true the
  same way.

## For module 09 and after: the GPT module 08 leaves

**Building, training, saving, loading, sampling.** From the project's top:

    import torch
    from models.gpt import GPT
    from experiments.language import train, save, load, generate, top_k, top_p
    from experiments.sequences import window_bits

    config = dict(vocab=65, context=256, layers=6, heads=6, width=192, dropout=0.2, bias=True, positions=True)
    model = GPT(**config)                     # scores = model(ids): ids (batch, T) int64 -> (batch, T, vocab)
    train(model, cfg, run, dev, ids, held)   # cfg: steps batch context lr warmup weight_decay clip every (lab.config)
    save(model, config, "runs/gpt/model.safetensors", steps=..., seed=..., val_bits=...)
    model, notes = load("runs/gpt/model.safetensors", dev)          # eval mode; notes["config"] is config
    drawn = generate(model, prompts, 200, torch.Generator().manual_seed(0), temperature=1.0, k=None, p=0.95)
    bits = window_bits(model, test_ids, model.context - 64 + 1, 64)  # bits per character, as 07.03 scores

The config above is 08.04's long run's best (2.226 bits per character on
the test text after 2800 steps at lr 0.002; its checkpoint is not
shipped, so a module that
needs a trained character model trains one in its run, or loads the
learner's from experiments/recorded/gpt/ or runs/gpt/ as sampling.py
does). load() needs only the file: the metadata holds the config.
generate(model, prompts, n, generator, temperature, k, p) is batched over
the rows of prompts (batch, P), reads the last model.context symbols at
each step (no cache of keys and values: each step is a whole forward, so
the cost grows with the window; module 11's), temperature 0 is greedy;
top_k(scores, k) and top_p(scores, p) are functions on the scores alone
(any vocabulary, GPT-2's 50257 too). GPT(..., positions=False) has no
position vectors and reads any length.

**Configuration** (GPT's arguments; GPT-2's own names in brackets): vocab
(vocab_size, n_vocab), context (n_positions, n_ctx), layers (n_layer),
heads (n_head), width (n_embd), dropout (resid_pdrop and embd_pdrop; GPT-2
has attn_pdrop on the attention weights too, which we do not have: it
matters only in training), bias (GPT-2 has every bias), positions. GPT-2
small is GPT(vocab=50257, context=1024, layers=12, heads=12, width=768,
dropout=0.0, bias=True): 124,439,808 weights, GPT-2 small's count (the
output tied to the embedding is counted once). A GPT of L blocks has V W +
context W + L (12 W^2 + 13 W) + 2 W weights (the test holds the formula
without positions).

**Parameter names and shapes, ours against GPT-2's checkpoint.** Read
from the published file itself, not from memory: the 14,283-byte header of
https://huggingface.co/openai-community/gpt2/resolve/main/model.safetensors
(fetched with two HTTP Range requests on 2026-11-24; the repository at
commit 607a30d783dfa663caf39e06633721c8d4cfcd7e; the file 548,105,171
bytes, its X-Linked-ETag 248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707,
which for a Git LFS file on that site is its SHA-256: 09.03's fetch pins
it after checking). 160 tensors, all F32, metadata {"format": "pt"}; the
names have no "transformer." in front (transformers' own state_dict has
it); there is no lm_head (tied to wte). For each block i (0 to 11), W = 768:

    ours                                   shape        GPT-2 (model.safetensors)     shape        how
    tokens.weight                          [V, W]       wte.weight                    [50257, 768] as is
    positions.weight                       [ctx, W]     wpe.weight                    [1024, 768]  as is
    blocks.i.norm1.weight / .bias          [W]          h.i.ln_1.weight / .bias       [768]        as is
    blocks.i.attention.query.weight        [W, W]       h.i.attn.c_attn.weight        [768, 2304]  columns 0:768, transposed
    blocks.i.attention.key.weight          [W, W]         "                                        columns 768:1536, transposed
    blocks.i.attention.value.weight        [W, W]         "                                        columns 1536:2304, transposed
    blocks.i.attention.query/key/value.bias [W]         h.i.attn.c_attn.bias          [2304]       0:768, 768:1536, 1536:2304
    blocks.i.attention.out.weight / .bias  [W, W], [W]  h.i.attn.c_proj.weight / .bias [768, 768]  weight transposed (square!)
    blocks.i.norm2.weight / .bias          [W]          h.i.ln_2.weight / .bias       [768]        as is
    blocks.i.mlp.up.weight / .bias         [4W, W]      h.i.mlp.c_fc.weight / .bias   [768, 3072]  weight transposed
    blocks.i.mlp.down.weight / .bias       [W, 4W]      h.i.mlp.c_proj.weight / .bias [3072, 768]  weight transposed
    norm.weight / .bias                    [W]          ln_f.weight / .bias           [768]        as is
    (none)                                              h.i.attn.bias                 [1, 1, 1024, 1024]  skip

Transposed: every weight of GPT-2's four Conv1D layers (c_attn, attn's
c_proj, c_fc, mlp's c_proj), which keep a weight as (inputs, outputs) and
compute x @ W + b (transformers' pytorch_utils.Conv1D: "Basically works
like a linear layer but the weights are transposed"; OpenAI's
src/model.py conv1d: tf.matmul(x, w) with w of shape [1, nx, nf]), where
nn.Linear keeps (outputs, inputs) and computes x @ W.T + b. attn.c_proj is
square, so a missing transpose loads without complaint and gives wrong
logits. The embeddings and the layer norms are as they are. h.i.attn.bias
is not a bias: it is the causal mask as a buffer of ones and zeros (12 of
them, 48 MB of the file); transformers no longer puts it in its
state_dict (4.57.6 here), the file still has it. c_attn holds query, key
and value side by side in that order (transformers splits it with
.split(split_size, dim=2) into query, key, value; OpenAI's tf.split(c, 3,
axis=2) into q, k, v). The test of 08.03 builds transformers'
GPT2LMHeadModel (random weights, a small configuration, eager attention),
moves its weights into our GPT with exactly this mapping (from_gpt2 in
tests/0803_...py: 09.03 can lift it) and gets the same logits to 1e-10 in
float64.

**The rest of what must agree, checked in the reference code.** GELU:
GPT-2's config says activation_function "gelu_new", which transformers'
ACT2CLS maps to NewGELUActivation, 0.5 x (1 + tanh(sqrt(2 / pi) (x +
0.044715 x^3))); OpenAI's src/model.py gelu is the same formula; ours,
models/gpt.py's gelu, is that formula (equal to F.gelu(approximate="tanh")
to the last bit here, and as fast). Not the exact erf GELU (F.gelu's
default). Layer norm eps 1e-5 (layer_norm_epsilon; OpenAI's norm(...,
epsilon=1e-5)); nn.LayerNorm's default. Pre-norm blocks with a last norm
(ln_f), as ours. Scores divided by sqrt(64), the head's size. The mask:
ours -inf, transformers torch.finfo(dtype).min, OpenAI -1e10: the same
softmax wherever a row has something unmasked, which the causal mask
always leaves. Positions are absolute, 0 to 1023 (no offset). The output
is the hidden state times wte transposed.

**What modules 10 and 11 are meant to replace, and where.** Module 10:
the layer norms (Block's norm1, norm2 and GPT's norm: nn.LayerNorm), the
MLP (models/gpt.py's MLP: up, gelu, down; SwiGLU adds a gate), the
positions (Positions, added in GPT.embed; rotary ones turn q and k
instead, in SelfAttention.qkv or self_attend), and grouped-query
attention (SelfAttention's key and value with fewer heads). Module 11:
self_attend, for F.scaled_dot_product_attention(q, k, v, is_causal=True)
(the tests of 08.01 and 08.02 already compare the two at 1e-12 in
float64), and a cache of keys and values for generate. GPT's start (the
loop in its __init__) finds the layers by name: "norm" in a name means a
norm, names ending in attention.out.weight and mlp.down.weight are the
two that add into the stream; a replacement that renames them must keep
the loop right. attention_maps (experiments/language.py) rebuilds each
block's weights from block.norm1, block.attention.qkv, a.mask and a.scale;
it must follow those changes too.

## For module 10 and after: GPT-2, its tokenizer and TinyStories

**GPT-2 and its tokenizer in three lines**, from the project's top, once
`python3 -m data.fetch gpt2` has run:

    import torch; from models import gpt2 as M; from tokens import gpt2 as T
    model, tok = M.load(torch.device("cpu")), T.load()          # GPT(**M.CONFIG) in eval mode; the tokenizer
    scores = model(torch.tensor([tok.encode("Hello, I'm a language model,")]))   # (1, T, 50257); tok.decode(ids)

model is models/gpt.py's GPT (vocab=50257, context=1024, layers=12,
heads=12, width=768, dropout 0): everything module 08 says about GPT
holds (generate, window_bits, save and load, its parameter names). The
weights come in by M.from_gpt2(tensors, 12, 768) on the dict
lab/safetensors.load_file gives; M.load(dev, path) takes another file of
GPT-2's names and shapes. tok.encode(text) treats "<|endoftext|>" in the
text as ordinary text (tiktoken's encode_ordinary); T.END is 50256, to
put between documents by hand. tok.table maps an id to its bytes;
tok.decode joins them (U+FFFD for a cut character). Module 12 fine-tunes
this model: train it with experiments/language.py's train on ids from
tok.encode (CONFIG has dropout 0: GPT(**{**M.CONFIG, "dropout": 0.1}) and
load_state_dict for GPT-2's own 0.1).

**Fetching** (data/fetch.py; every file checked against its pinned size
and SHA-256 before it is kept; a dropped download carries on with an
HTTP Range request; a generic User-Agent, no account, no token):

    python3 -m data.fetch gpt2          vocab.json 1,042,301, merges.txt 456,318, model.safetensors 548,105,171 bytes
                                        https://huggingface.co/openai-community/gpt2/resolve/607a30d783dfa663caf39e06633721c8d4cfcd7e/
                                        73 s here
    python3 -m data.fetch tinystories   train.txt 67,108,864 (bytes 0 to 67,108,863 of TinyStories-train.txt),
                                        valid.txt 19,447,282 (TinyStories-valid.txt whole)
                                        https://huggingface.co/datasets/roneneldan/TinyStories/resolve/f54c09fd23315a6f9c86f9dc80f725de7d8f9c64/
                                        11 s here

into $LEARN_CACHE (default ~/.cache/systems-from-scratch)/gpt2/ and
/tinystories/. A dataset of separate files says "each": True in
DATASETS, a range of a larger file "ranges": {local name: (name on the
server, first byte)}; fetch_each does both. Module 10's SmolLM2-135M fits
the same form: one model.safetensors of 269,060,552 bytes (at commit
93efa2f097d58c2a74874c7e644dbc9b0cee75a2 of HuggingFaceTB/SmolLM2-135M on
2026-11-24, X-Linked-ETag 80521b40...5da1, to be checked as GPT-2's was),
plus its tokenizer files. Read from that file's header (two Range
requests, 30,536 bytes): 272 tensors, every one BF16; numpy has no
bfloat16 and lab/safetensors.py's DTYPES has no "BF16", so module 10 must
add it (the 16 bits are a float32's top half: read as uint16, shift into
uint32, view as float32). Names model.embed_tokens.weight [49152, 576],
model.layers.i.self_attn.q_proj [576, 576], k_proj and v_proj [192, 576]
(3 key/value heads of 64 for 9 query heads), o_proj [576, 576],
mlp.gate_proj and up_proj [1536, 576], down_proj [576, 1536],
input_layernorm and post_attention_layernorm [576], no lm_head (tied).
Its weights are nn.Linear's (outputs, inputs): no transposes, unlike
GPT-2's Conv1D; a missing transpose cannot happen, a wrong head split can.

**Speeds on this CPU** (Apple M4 Pro, 10 threads, load about 2; GPT-2
small in float32, no cache of keys and values):
- forward, scoring: 1 x 1024 tokens 0.23 s (4,500 tokens a second); 4 x
  256 0.14 s (7,400); 16 x 64 0.14 s (7,400); 16 x 128 0.25 s (8,200);
  1 x 64 0.024 s (2,700). Scoring Tiny Shakespeare's test text (17,995
  tokens, windows of 1024, warm 64) 4.8 s.
- generating (experiments/language.py's generate, a whole forward a
  step; load 8 to 11): 1 row, 64 tokens after 32: 2.2 s, 29 tokens a
  second (35 ms a step); 8 rows: 7.2 s, 71 tokens a second (113 ms a
  step); 1 row, 32 tokens after 512: 4.2 s, 7.7 a second (130 ms a step:
  every step reads the whole window again). A cache of keys and values is
  module 11's. The TinyStories long run's model (4.27M weights): one
  story of 200 tokens 1.0 s (204 tokens a second), 16 at once 5.8 s
  (549).
- loading: 1.3 s (load_file 0.06 s from the page cache, the rest GPT's
  random start and load_state_dict), peak memory 1.2 GB.
- the tokenizer: 4.7 MB of text a second with its cache (0.24 s for Tiny
  Shakespeare), 1.2 MB without; reading its files 0.06 s and making its
  Unicode classes 0.07 s, once a process.
A training step of GPT-2 small was not measured here (module 12's).

**TinyStories** (data/tinystories.py; `python3 -m data.fetch tinystories`):
stories("train") 74,394 stories, stories("valid") 21,990 (lists of
strings, in file order; the train file's last, cut story dropped, the
empty ones left out); tokenizer(size) -> (merges, table), 09.01's BPE
learned on the first 10,000 training stories (LEARN_FROM) one to a
line, size - 1 symbols, the last id, size - 1, is END; tokens(split,
size) -> numpy uint16, every story's tokens then END. size 4096:
16,709,577 training tokens, 4,831,485 held-out, 3.95 bytes a token;
stories median 194 tokens (90% 353 or fewer, 99% 645, longest 1,253;
80% fit in 256, 97% in 512). Tokenising takes 9 s (merges 5 s, train 2.9
s, valid 1.0 s) and is kept in the cache folder: bpe4096.json (the merged
pairs in order), train-bpe4096.npy, valid-bpe4096.npy; read back in
milliseconds. Delete them after changing tokens/bpe.py or LEARN_FROM:
nothing checks that they are stale. The stories have curly quotes and
dashes (about 1 character in 2,500 is not ASCII), so table lookups are bytes and
decode is 09.01's. The long run's checkpoint, when the learner has made
it: experiments/recorded/tinystories/model.safetensors, GPT(vocab=4096,
context=256, layers=4, heads=8, width=256), loaded by language.load;
it needs tokenizer(4096) for its text.

## Tests

`./learn test research`: 27 tests, all pass, 3 min 22 s. Each runs its
differential checks first, in a fresh python with the project and tests/ on
its path (`inside(S)`, S = tests/support.py; same_op compares an operation's
values and gradients with PyTorch's at 1e-6 in float64, whole training
steps compare every parameter after every step), then its experiment on
short settings (thresholds over fixed seeds, never exact floats), then the
same experiment on PyTorch (`on_torch`) for every engine-era script.
`./learn check-skeleton research`: every lesson cut out still builds and its
test fails at its stub (23 s). `./learn check-timeline research`: the
project at every lesson compiles, imports, runs every experiment it has on
short settings, has exactly the engine names of NAMES, and gives the
ordinary errors above (46 s). The tests need PyTorch and safetensors
(`pip install safetensors`); the project itself needs only numpy.

With module 06 (timed with other agents' runs going, load average 4 to 8):
`./learn test research` 31 tests, all pass, 5 min 11 s, module 06's four
2 min 2 s (06.01 27 s: the differential checks, conv with 2 seeds, conv on
PyTorch; 06.02 7 s: lab.device and lab.clock against a stand-in torch, the
step against PyTorch at 1e-10 to 1e-12, switch twice, byte for byte;
06.03 31 s: the record reader on a file written by the test, crop_flip,
train_epoch and evaluate, then with CIFAR-10 the real files' shapes and
classes, cifar with 2 seeds and 10 passes, and a tiny run twice, byte for
byte; 06.04 57 s: the networks' shape, weights and shortcut, the recorded
long run's files and result, then the short run). 06.03 and 06.04 need
CIFAR-10 (`need(t, "cifar10")`, after the checks that do not). The long
run is rerun only with LEARN_RERUN_LONG=1 (about 40 minutes).
`./learn check-skeleton research` ok, 27 s (31 lessons, each fails at its
stub). `./learn check-timeline research` ok, 70 s; the project has 50
files at 06.01, 54 at 06.02, 57 at 06.03 and 98 at 06.04 (41 of them the
recorded run). `./learn selftest` ok (269 tests). `./learn check` reports
exactly four problems, `research/06.0N: test has no lesson doc`, until the
pages are written; nothing else.

With module 07 (timed with other agents' runs and a virtual machine going,
load average 9 to 28): `./learn test research` 35 tests, all pass, 9 min
2 s; module 07's four 2 min 10 s. 07.01 2 s: the text's size and SHA-256,
the reader (65 characters, the three parts are the whole text in order),
pair_counts against collections.Counter, probabilities, bits, sample, then
bigram's ladder and twice byte for byte. 07.02 52 s: context_codes and
NGram's counts against direct counts at contexts 0 to 3, the pair counts
against 07.01's table, chances adding up to 1 after a seen and an unseen
context, EM against the best of a grid, bits, contexts, context_bits,
sample and nearest against direct computations; the recorded long run's
files, settings and result (every seed below interpolation at 5 and 8,
the pair model at 1); then nplm at contexts 1 and 5 (2 seeds, 1500 steps:
training bits fall, held-out bits turn up, the network far below add-k at
5, mixed below interpolation) and a tiny run twice, byte for byte. 07.03
41 s: RNN against torch.nn.RNN on copied weights in float64 at 1e-10
(states, the last state, and the gradients of the inputs, the first state
and every weight), windows and window_bits against direct sums,
recall_task, gradient_back against a direct backward (and the weights'
.grad left alone); then rnn (2 seeds, 300 steps: text below 3 bits, recall
right at T = 2 and near chance at 40, the gradient table's two ends, the
reads flat past 16) and a tiny run twice. 07.04 35 s: attend and Additive
against the formula written out by loops, the plain decoder ignoring the
encoder's states, the attention decoder's step against its definition,
teacher forcing with a model's own symbols against generate; then
attention (2 seeds, 800 steps, lengths 2, 10, 30) and a tiny run twice.
Again later with the machine lighter (load about 5): 07.01 to 07.04 in
1.4, 19.6, 23.3 and 23.9 s. The long run of 07.02 is rerun only with
LEARN_RERUN_LONG=1 (about 20 minutes). `./learn check-skeleton research` ok, 38 s (35 lessons, each
fails at its stub). `./learn check-timeline research` ok, 107 s; the
project has 101 files at 07.01, 145 at 07.02 (41 of them the recorded
run), 147 at 07.03 and 150 at 07.04; 06.04 still has 98 (track.py puts
"experiments/recorded/nplm/*" before 06.04's wider glob). `./learn
selftest` ok (269 tests). `./learn check` reports exactly eight problems,
`research/06.0N` and `research/07.0N: test has no lesson doc`; nothing
else.
With module 07's pages (lessons agent, 2026-11-24): `./learn check` ok, no
problems; `./learn check-timeline research` ok (101, 145, 147 and 150
files at 07.01 to 07.04); `./learn check-skeleton research` ok; `./learn
selftest` ok (269 tests). Module 07's figures come from
art/research/figs07.py (about four minutes of runs; RESEARCH_FIGS_CACHE
keeps them while drawing), its cover from art/outlines/research_art.py,
which now counts the pair model's 3.599 again and reads 07.02's recorded
run. Verifying 07.01 to 07.04 replays nplm, rnn and attention twice each,
the 5000-step rnn once (about 130 s) and the Break its: about ten minutes.

With module 08 (a virtual machine taking 4 to 5 cores, load average
about 5): `./learn test research` 40 tests, all pass, 8 min 43 s; module
08's five 2 min 49 s (08.01 15.2 s, 08.02 38.5, 08.03 42.2, 08.04 39.9,
08.05 33.3). An earlier full run at load 6 to 11 took 11 min 15 s. Module
08's five tests, each its differential
checks first (in float64 unless said), then its experiment: 08.01:
causal_mask; self_attend against loops over positions for every head,
with and without the mask and the division (1e-12), and against
F.scaled_dot_product_attention (1e-12); SelfAttention against its
definition; a later position changes nothing before it (torch.equal), in
SelfAttention and in OneHead, and does without the mask; last_bits
against a direct sum; at_the_start's spreads; then self_attention (2
seeds): no mask lower as trained by 0.15 and higher from the past by
0.3, not divided higher by 0.08, the masked text not one character over
and over and the unmasked one's so, the last-character change 0 and not
0; a tiny run twice, byte for byte. 08.02: gelu against F.gelu
(1e-14); SelfAttention with 3 heads against tests/support.py's loops and
against F.scaled_dot_product_attention (1e-12); MLP; a Block and a GPT
without positions against support.gpt_numpy (1e-10; in float32 1e-5);
causality; the weight count V W + L (12 W^2 + 13 W) + 2 W and GPT-2's
start (sds 0.02 and 0.02 / sqrt(2 L)); attention_maps (rows add to 1, 0
above the diagonal, the first block's output from them) and looks on a
known map; then heads (2 seeds): the stack worse by 0.3, 4 blocks better
by 0.05, 4 heads below 1 head; the logged weights' shape; a tiny run
twice. 08.03: Positions and its refusal; a GPT with positions against
gpt_numpy (1e-10); causality; shuffled for 1 block (same), 2 blocks and
positions (not); transformers' GPT2LMHeadModel against our GPT through
the GPT-2 mapping (1e-10; skipped with a printed line if transformers is
not installed); then positions (2 seeds): positions lower by 0.03, the
shuffle line's three cases, the ValueError, bits rising past the
context; a tiny run twice. 08.04: held_bits; train's held rows; save and
load (the same scores; the safetensors library reads the file, its
metadata and every tensor); ladder's first rows equal to 07's; lowest;
the recorded long run (every file, the curve in every log, no weights;
without dropout every seed's curve turns up by more than 0.02 before the
end, dropout's validation bits are the lower, every seed of the setting
chosen on validation below 2.283); then gpt (the default, 2 seeds): below the pair model, the
checkpoint and curves written, read back the same, the validation curve
falling; a tiny run twice, checkpoint included, byte for byte;
LEARN_RERUN_LONG=1 runs the long run again. 08.05: top_k and top_p
against a direct computation on two rows of scores for every k and eight
p; generate against counted draws (4000) from a fixed distribution with
each cut and a temperature, greedy against an argmax loop, k = 1 equal
to greedy, the same generator the same symbols, the window cut to
model.context; repeats; continuation_bits against a direct sum; then
sampling (2 seeds, checkpoint=none): greedy's perplexity below half the
text's and its loops, pure sampling within 15% of the text, t = 0.7,
top-k 5 and the nucleus below 95% of pure sampling; a checkpoint written
by save is used when given; a tiny run twice.
08.03's comparison with transformers imports it in the test's own python
(a few seconds; the tests may use it, the project never does). The long
run is rerun only with LEARN_RERUN_LONG=1 (about an hour). `./learn
check-skeleton research` ok, 33 s (40 lessons, each fails at its stub:
08.01 at causal_mask, 08.02 at gelu, 08.03 at Positions, 08.04 at
held_bits, 08.05 at top_k). `./learn check-timeline research` ok, 2 min
16 s (5 min 12 s at load 10 to 30); the project has 153 files at 08.01, 154 at 08.02, 155 at 08.03,
170 at 08.04 (13 of them the recorded run, which track.py places at 08.04
with its glob first) and 171 at 08.05; 06.04 still 98 and 07.02 145.
`./learn selftest` ok (269 tests). `./learn check` reports exactly nine
problems, `research/07.0N` and `research/08.0N: test has no lesson doc`;
nothing else.
With module 08's pages (lessons agent, 2026-11-24; another agent training
on the machine, load 7 to 13): `./learn verify --fresh research 08` ok in
534 s (08.01 55 s, 08.02 154 s with its seeds=3 run, 08.03 119, 08.04
103, 08.05 103); inside it 08.01's default printed 44 s and 08.02's 2-seed
default 43 s. `./learn test research 08` all 5 pass, 3 min 46 s, after
the 2-seed cut. `./learn check` ok, no problems; `./learn check-skeleton
research` ok; `./learn check-timeline research` ok (153 to 171 files at
08.01 to 08.05, as before); `./learn selftest` ok (269 tests). Two things
a writer here meets: `./learn verify --static` takes another project's
file named in backticks (`model.py`, `gpt_train.py`) for this project's,
so a Go deeper line that names one needs a `mention ... outside`
annotation; and a transcript pasted by hand can be a character off (a
line of 300 sampled characters was): check each line against the run's
saved output before verifying.

With module 09 (load average 4 to 10, other agents' runs going): `./learn
test research` 44 tests, all pass, 12 min 43 s; module 09's four 2 min 12
s (09.01 34.2 s, 09.02 13.4, 09.03 58.0, 09.04 26.8). Module 09's four tests, each its checks
that need no download first, then `T.need(t, "gpt2" or "tinystories")`:
without the files the test fails there with `missing: ... Fetch it once
with python3 -m data.fetch ...`, as 06.03 and 06.04 do without CIFAR-10
(the planner's decision after the code was built: a pass that did not
compare the ids or the logits would say more than it checked; the tests
skipped at first, and need() still takes skip=True). 09.01: pieces join back to 3,000 random strings
from every part of Unicode; pairs, merge (against a tuple version on 200
random cases); train_simple and train against tests/support.py's
bpe_reference (written apart: sorted counts, tuples) on 20,000 characters
of Shakespeare and on the random Unicode text, merge lists equal in
order; ties to the smaller pair; encode against bpe_replay (every merge
applied in learned order) and decode back, on held-out Shakespeare and
100 random strings; unseen and per_character against direct counts; then
bpe (2 seeds, 200 steps, vocabularies to 1024, the GPT on 1024 tokens):
words in a window, the unseen counts to the digit, the fast trainer 50
times sooner with the same first merges, bytes per token growing and
higher on training text, every round trip, BPE 0.2 bits per character
below characters on every seed; a tiny run twice, byte for byte. 09.02:
byte_symbols; classes against unicodedata on every code point; SPACE is
str.isspace() without 0x1c to 0x1f, 25 code points; split's pieces
against the regex module's GPT-2 pattern on 3,000 random strings and the
built corpus; Tokenizer on toy files (and a file with merges out of order
refused); data/fetch.py's fetch_each against a server on 127.0.0.1 that
serves at most 3,000 bytes a request (a download carried on from where
it stopped, a range of a larger file, a wrong SHA-256 not kept); then,
with GPT-2's files, the ids against every reference (above) and the
Unicode-version scan; then tokenizer (repeats=1, size=1024). 09.03:
load_file on a good file and three bad ones, in a fresh python its peak
on 96 MB (under 1.3 times the file); loops, perplexity against a direct
sum; from_gpt2 with transformers' GPT2LMHeadModel (random weights, a
small configuration) at 1e-10 in float64, a square weight untransposed
gives other logits, a non-square one is refused; then, with GPT-2's
files, the real logits against transformers' (above), the missing
transpose far off; then gpt2 (the default): the wrong mapping 1 bit per
character worse, GPT-2 below 2.0 on the test text, greedy below a
quarter of pure sampling's perplexity and looping in 25% or more,
t=0.7, top-k 40 and the nucleus below pure sampling; a tiny run twice.
09.04: data/tinystories.py on small files the test writes (a LEARN_CACHE
of its own, DATASETS' sizes patched: stories cut, the last cut piece and
empty ones dropped, merges kept and read back, tokens with END, kept and
read back the same); kgram_hashes against the polynomial written out;
shared_run against a direct search on 30 random cases (half with a
planted copy); tell against generate with the same generator; the
recorded long run's files and result; then, with TinyStories, the real
counts (74,394 and 21,990 stories, END after each, tokens decoding back
to the stories); then tinystories (the default, checkpoint=none: so a
learner's runs/ cannot change it): bits per byte below 2.2, the
checkpoint and curves written, 8 stories measured; a tiny run twice.
LEARN_RERUN_LONG=1 runs the long run again (about 45 minutes).
The references: tiktoken was installed for this with `python3 -m pip
install --user tiktoken` (0.14.0; pip did not refuse); transformers
4.57.6 and the regex module were already here. The project never
imports any of them.
`./learn check-skeleton research` ok, 42 s (44 lessons, each fails at its
stub: 09.01 at pieces, 09.02 at byte_symbols, 09.03 at loops, 09.04 at
kgram_hashes). `./learn check-timeline research` ok, 3 min 16 s at load 6
to 8; the project has 174 files at 09.01, 176 at 09.02, 178 at 09.03 and
194 at 09.04 (14 of them the recorded run); 06.04 still 98, 07.02 145,
08.04 170, 08.05 171. experiments/tokenizer.py has no regions, so
track.py names it in FILES_FROM (09.02); `./learn check` found it before
that line. `./learn selftest` ok (269 tests). `./learn check` reports
exactly nine problems, `research/08.0N` and `research/09.0N: test has no
lesson doc`; nothing else.
With module 09's pages (lessons agent, 2026-11-24; other agents training,
load 9 to 16): `./learn verify --fresh research 09` ok in 315 s (09.01 82
s, 09.02 29, 09.03 124 with its Break it's second run of the default,
09.04 80); an earlier fresh run 303 s. `./learn check` ok, no problems;
`./learn check-skeleton research` ok (56 s); `./learn check-timeline
research` ok (3 min 34 s; 174, 176, 178 and 194 files at 09.01 to 09.04);
`./learn selftest` ok (269 tests). Every map was drawn again (the data row
has seven pieces now). 09.02's tiktoken session needs="gpt2 tiktoken": on
a machine without tiktoken that lesson is "missing".

## For the harness work and module 06

- verify_tools() names python3 and numpy only. MNIST is a download, not a
  program, so `needs=` cannot see it; the plan's `./learn fetch` and a
  "missing" for downloads are still to do (data/fetch.py is what it should
  call). Since module 06: verify_tools() also names `torch` and `cifar10`
  as empty programs when this machine has them (see "Conventions from
  06.02 on", Verify), a work-around inside the track. What the harness
  would need to do it properly: verify_tools(lesson) (tools for one
  lesson), or a track hook that `needs=` asks about a name, so a Python
  package or a download can be "missing" without a program on PATH. The
  same hook would let 03.01 to 05.04 say needs="mnist".
- `models/` exists from 06.02 (convnet.py, then resnet.py at 06.04); 00 to
  05 build their small networks inside each experiment (deep.py and loop.py
  take the engine as an argument). 06.02's "one import" is true of every
  engine-era script here.
- `experiments/` is the plan's `papers/<name>/`: one file per lesson, since
  most of 00 to 05 are not papers.
- (07) FILES_FROM places a file by the first glob that matches it, in the
  dict's order, and 06.04's "experiments/recorded/*" matches every later
  recorded run. track.py's module-07 part rebuilds FILES_FROM with
  "experiments/recorded/nplm/*" first. What the harness could do instead:
  let the longest (most specific) matching pattern win, as an exact path
  already does; then each module's recorded run needs only its own line.
- (07) Module 07 needs no download, so its session blocks need only
  needs="torch" from 07.02 on; 07.01 is numpy only and needs nothing.
- (08) The same glob order again: track.py's module-08 part puts
  "experiments/recorded/gpt/*" first. Module 08 needs no download either:
  needs="torch" for all five lessons. gpt.py writes its checkpoint,
  model.safetensors, into the run's folder, and so into
  experiments/recorded/gpt/ when the long run is made again; the harness
  reads the disk, not git, so track.py adds
  "experiments/recorded/*/model.safetensors" to HIDDEN: never listed,
  shown or materialized. The recorded one was moved out before the commit
  (no weights are shipped).
- (09) The glob order once more: track.py's module-09 part puts
  "experiments/recorded/tinystories/*" first in FILES_FROM; HIDDEN's
  "experiments/recorded/*/model.safetensors" already hides its checkpoint.
- (09) needs=: 09.01 needs "torch" only (Tiny Shakespeare ships); 09.02
  and 09.03 needs="torch gpt2"; 09.04 needs="torch tinystories".
  pytorch_era_tools() now writes one empty program for each entry of
  track.py's TOOLS dict (torch, cifar10, gpt2, tinystories); a module
  that adds a download adds an entry. need(t, name) fails with "missing:"
  for these too (see Tests). The same harness hook as before would
  make all of this unnecessary.
- (09) Region titles that are ordinary words, for the lessons agent's
  lead-ins (they match case-insensitively): load (language.py 08.04,
  tokens/gpt2.py 09.02, models/gpt2.py 09.03), tokens, stories, pattern,
  split, merge, pairs, pieces, train (language.py 08.01, tokens/bpe.py
  09.01), encode and decode (data/shakespeare.py 07.01, tokens/bpe.py
  09.01). No lesson has two regions of one name.
- (09) check-timeline runs tokenizer and gpt2 only where GPT-2's files
  are in the cache, tinystories where TinyStories is (DATASET_OF), and
  expects the "is missing" line elsewhere, as for CIFAR-10.

## Module 10: today's architecture

Built on 2026-11-24 on the machine above (Apple M4 Pro, Python 3.12.7,
torch 2.10.0, numpy 2.4.3; transformers 4.57.6 and tokenizers 0.22.2 for
the tests only), with two other agents' work running: every time below
has the load average beside it. The learner's code imports numpy, torch
and the standard library only.

**What is new, and where.**

```
models/gpt.py           10.01   RMSNorm (region); GPT's norm="rms" (Block's norm1, norm2, GPT's norm)
                        10.02   Rotary (region); positions="rotary" and base (SelfAttention's rotary, in qkv)
                        10.03   SwiGLU (region); mlp="swiglu" and hidden (Block's mlp)
                        10.04   kv_heads (SelfAttention's key and value, the view and repeat in qkv)
models/smollm.py        10.04   CONFIG, from_smollm, load: SmolLM2-135M's published weights in GPT
tokens/smollm.py        10.04   split, Tokenizer (regions), END, load: SmolLM2's tokenizer, from tokenizer.json
lab/safetensors.py      10.04   bfloat16 (region); DTYPES["BF16"] (one-line @from); load_file widens BF16
                                (an @from 10.04 block inside 09.03's block inside the 02.05 region)
data/fetch.py           10.04   smollm2 (an @from block): four files, pinned
experiments/language.py 10.01   compare: GPTs that differ in one piece, trained, timed and scored alike
experiments/            10.01   rmsnorm.py (written_layer_norm, norm_times, centring, uncentred)
                        10.02   rotary.py (neighbours: the paper's own form)
                        10.03   swiglu.py (gates)
                        10.04   smollm.py (no regions; FILES_FROM)
                        10.05   ablation.py (table); recorded/ablation/, the long run
tests/support.py        10.01   gpt10_numpy and its pieces: rms_norm, rotate_numpy, silu_numpy, attention10_numpy
```

**GPT's new arguments** (models/gpt.py; each default is module 08's
piece): `norm="layer"` or `"rms"`; `positions=True` (08.03's learned
table), `False` (none) or `"rotary"`, with `base=10000.0` (rotary's
angles, theta_i = base^(-2i/d)); `mlp="gelu"` or `"swiglu"`, with
`hidden=None` (SwiGLU's inner width, 8 x width // 3 when None); and
`kv_heads=None` (heads of keys and values; None: as many as query
heads). Block and SelfAttention take the same ones (SelfAttention's
`rotary` is the base, or None). A checkpoint written by 08.04's or
09.04's runs stores a config without them and loads as before
(language.load builds GPT(**config)). Measured: the default model is
built draw for draw as before, so every earlier number is unchanged:
08.03's positions, 08.04's gpt and 08.01's self_attention, run on short
settings before and after the change, gave the same bytes in every
log.jsonl, summary.json and checkpoint (only config.json's out path
differed); the earlier lessons' views of models/gpt.py are unchanged at
08.01, 08.02, 08.03, 08.05 and 09.04 (harness/timeline.py's lines_at,
compared before and after). `positions` is now tested with `is True`
(a "rotary" string is truthy). The signatures grow one argument line a
lesson: each `def __init__` is `... positions=True,` / `norm="layer",` /
`base=10000.0,  # @from 10.02` / ... / `):`, so 10.01 shows the
signature with `norm` alone and each later lesson adds its line, with
the earlier lessons' one-line signatures kept as @else parts (nested as
kilo.c nests them: a later @from inside an earlier one's body).

What stays right (the three the planner named):
- GPT.__init__'s start still finds layers by name: RMSNorm's weight is
  named norm1.weight, norm2.weight, norm.weight ("norm" in it: left at 1
  by the loop, RMSNorm starts it at 1); SwiGLU's three are mlp.gate,
  mlp.up and mlp.down, and mlp.down.weight is still the one that adds
  into the stream (started by sqrt(2 x layers) smaller; the 10.03 test
  checks it); key and value of fewer heads are ordinary weights.
- attention_maps (experiments/language.py) is unchanged and right for
  every variant: SelfAttention.qkv returns the queries and keys already
  turned (rotary) and the keys and values already repeated to every
  query head (grouped), so self_attend(*a.qkv(block.norm1(x)), a.mask,
  a.scale) is the block's attention; the 10.02 and 10.04 tests rebuild
  the first block's output from its maps (1e-12).
- generate reads the last `model.context` symbols. A rotary model has
  no table to run out of and reads any length (10.02 part 3), but it
  gets worse past the length it was trained on, so `context` keeps its
  meaning: the window the model was trained on, the longest it is good
  for; generate keeps to it. SmolLM2's context is 8192, its config's
  max_position_embeddings (its model card's table calls it
  SmolLM2-135M-8k).

**The comparisons of 10.01 to 10.04** all use experiments/language.py's
compare on 08.04's default GPT (4 blocks of 4 heads, width 64, windows
of 64, bias=True, learned positions, GELU MLP: 208,320 weights) with
08.04's training (AdamW 0.003, weight decay 0.1 on the matrices, warmup
50 then a cosine to 0, clipped to 1, batches of 32 windows from random
places of the training text), 150 steps, 3 seeds, the variants taking
turns seed by seed; bits per character on the test text by window_bits
with warm = context / 4 (each character with 16 or more before it, as
08.04 scores); ms a step = the training's wall clock (lab.clock) over
the steps, after an untimed warm-up step. Same seed: the same starting
draws for every variant whose shapes match (torch.manual_seed before
each), the same batches (run.rng). The base row is therefore the same
three runs in all four lessons: `3.563 +- 0.004889` (min 3.559, max
3.568). Times a step are the busy machine's (load 6 to 16 while these
ran): compare them only inside one run, where the variants took turns.

**10.01 RMSNorm: normalising with less (Zhang and Sennrich 2019).**
experiments/rmsnorm.py. Default run 38.2 s at load 8.4 to 9.1, 36.6 s
at load 8.8 to 11.7 (the same digits but for the times):
1. RMSNorm against torch.nn.RMSNorm on 64 vectors of 64 (float64): the
   largest difference 0; against the formula 1.78e-15. [3, 4, 0, 0]
   (root mean square 2.5): RMSNorm [1.2, 1.6, 0, 0], layer norm [0.7001,
   1.2603, -0.9802, -0.9802]; [5, 6, 7, 8]: RMSNorm [0.7581, 0.9097,
   1.0613, 1.213], layer norm [-1.3416, -0.4472, 0.4472, 1.3416]: RMSNorm
   keeps the vector's direction, layer norm moves it to around 0 first.
2. The norm alone, forward and backward (the median of 100 calls, the
   four taking turns), ms: 32 x 64 x 64 (the GPT's activations):
   nn.LayerNorm 0.290, layer norm written out (written_layer_norm, the
   same operations as RMSNorm plus the mean) 1.121, RMSNorm 0.763,
   nn.RMSNorm 0.763; 8 x 512 x 576 (SmolLM2's width): 0.870, 3.572, 2.587,
   2.453. RMSNorm takes 0.68 and 0.72 of the written-out layer norm's
   time, and 2.64 and 2.97 times nn.LayerNorm's. An earlier run (200
   calls, load 6 to 9): 0.260, 1.017, 0.718, 0.696 and 0.744, 2.486,
   1.702, 1.662 (0.71 and 0.68; 2.76 and 2.29). So the paper's saving is
   there in the arithmetic, about 30% when both are written alike, and
   PyTorch's layer norm, one fused kernel, is faster than either.
3. Trained (150 steps, 3 seeds): layer norm `3.563 +- 0.004889`, RMSNorm
   `3.561 +- 0.01412` (min 3.547, max 3.576): -0.0020, t = -0.2. ms a
   step 34.1 +- 7.07 against 37.9 +- 1.31, x1.111, t = +0.9 (one of layer
   norm's seeds at 42.3 under the load). 576 weights fewer (9 norms'
   biases). An earlier default of 200 steps (load 6 to 9): 3.474 against
   3.471, t = -0.5; 28.8 against 32.9 ms, x1.146, t = +3.0.
4. What the mean did. |mean| / rms of the vectors each norm reads (seed
   0, 125 windows of the test text), block 1's norm1 and norm2, then the
   rest: layer-norm model 0.047, 0.049, then 0.018 to 0.021; RMSNorm
   model 0.109, 0.109, then 0.083 to 0.121. The vectors the layer norms
   read are already nearly centred (their mean 2 to 5% of their size).
   The trained layer-norm model with every norm dividing by the root
   mean square without taking the mean away (gains and biases kept,
   experiments/rmsnorm.py's uncentred): 3.5683 as trained, 3.5684
   without. The mean step was doing almost nothing in the trained model.
Longer: the 600-step spike (2 seeds, below) +0.013 (t = +0.5); the long
run (10.05) +0.0133 (t = +2.6) and x1.18 a step. As found: the paper's
"comparable performance" held at every budget here (within 0.013 bits,
inside the noise); its time saving did not, in a whole step on this CPU:
RMSNorm made the step 11 to 18% slower, because PyTorch's nn.LayerNorm is
one fused kernel and RMSNorm here is four operations; the paper's own
Transformer saving was 7% (table 4), in TensorFlow on a GPU, and its
section 7 says the gain depends on "the framework, hardware, neural
network architecture and relative computational cost of other
components". Why every open model uses it anyway is not measured here
(a fused RMSNorm kernel, on a GPU, is the usual answer; not run).

**10.02 Rotary positions: turning instead of adding (Su et al. 2021).**
experiments/rotary.py. Default run 29.7 s at load 8.9, 37.1 s at load
9.5 (the same digits but for the times):
1. Exact, float64, 8 x 40 queries and keys of 16: the largest change in
   a score when both move along by 1, 7 or 1000 places 3.79e-13 (the
   angles of place 1000 rounded; 1e-15 for small moves); in a vector's
   length 8.88e-16; between the paper's neighbours and ours with the
   numbers reordered 3.55e-15; and, for scale, between turned and
   unturned scores 25.1.
2. Trained: learned positions `3.563 +- 0.004889`, rotary `3.248 +-
   0.007674` (min 3.24, max 3.255): -0.3151, t = -60.0. ms 26.1 against
   30.9, x1.182, t = +2.8. 4,096 weights fewer (the table).
3. Past the length trained on (64), seed 0: learned, a window of 256:
   "ValueError: 256 positions, but there are learned vectors for 64";
   rotary, windows of 64, 128 and 256, bits at positions 0 to 63 / 64 to
   127 / 128 to 255: n = 1 3.265; n = 2 3.271 / 3.303; n = 4 3.262 / 3.300
   / 3.562. It reads any length, and gets worse past the length it was
   trained on: a little at twice it, 0.3 bits at four times. (08.03's
   model without positions, at windows of 32: 3.399, 3.537 at 2x, 3.682
   at 4x: the same shape.)
Longer: 600 steps -0.242 (t = -11.2), 1200 steps -0.158 (t = -10.5), the
long run -0.060 (t = -5.6) and x1.52 a step. As found: "faster
convergence" held, strongly: the gap is widest early and narrows with
training, and is still there at 2000 steps of a model four times the
size. "Flexibility of sequence length": the model runs at any length,
but it is no better past its training length than 08.03's model
without positions; the paper does not measure this beyond its
1024-token row. The time: our Rotary rebuilds its angles at every call,
which costs 18 to 50% a step here (For module 11).

**10.03 A gated MLP: SwiGLU (Shazeer 2020; Dauphin et al. 2017).**
experiments/swiglu.py. Default run 23.0 s at load 7.4, 31.2 s at load
8.3 (the same digits but for the times):
1. The weights of one MLP: width 64 with biases, MLP (inner 256) 33,088,
   SwiGLU (inner 170) 33,044, -44; without biases 32,768 / 32,640, -128;
   width 576 with biases 2,657,088 / 2,657,856, +768; without biases
   2,654,208 / 2,654,208, +0 (SmolLM2's: 1536 = 8 x 576 / 3 exactly).
2. Trained: GELU MLP `3.563 +- 0.004889`, SwiGLU `3.596 +- 0.01129` (min
   3.59, max 3.609): +0.0333, t = +4.7: behind, at 150 steps. ms 22.9
   against 21.7, x0.947, t = -0.8. 176 weights fewer.
3. The gates (seed 0, 125 windows): the share of silu(gate) under 0.1 in
   size, and over 1: block 1 0.262 and 0.059; blocks 2 to 4 0.401 to
   0.425 and 0.003 to 0.004. About two fifths of the inner numbers are
   shut for any one character in the deeper blocks.
Longer: 600 steps -0.044 (t = -1.9), 1200 steps -0.049 (t = -3.5), the
long run -0.067 (t = -10.9), the largest single change there, and x0.91
a step. As found: the paper's gain (1.944 against GELU's 1.983, its
table 1, at 65,536 steps of a T5 base) held once the model had trained
a while; at 150 steps SwiGLU is behind. Why it starts slower is
reasoned, not measured: at the start gate and up are both small, and
their product is smaller still, so the gated MLP adds almost nothing
to the stream until its weights grow. Its time a step is the MLP's (the
same multiplies, 3 x 64 x 170 against 2 x 64 x 256).

**10.04 Grouped-query attention, and loading a current open model
(Ainslie et al. 2023; Allal et al. 2025).** experiments/smollm.py.
Default run 33.2 s at load 9.6 to 10.6, 36.9 s at load 8.9 (the same
digits but for the times):
1. Heads (2 seeds): 4 key/value heads (each query head its own)
   208,320 weights, 512 numbers kept a token (2 x 4 heads x 16 x 4
   blocks), `3.565 +- 0.004595`; 2 key/value heads 191,680, 256 kept,
   `3.566 +- 0.006775`: +0.0011, t = +0.2, x1.003 a step, 16,640 weights
   fewer. With 3 seeds (the first default, 45 s at load 6.5): 3.563
   against 3.565, +0.0023, t = +0.6. Longer: 600 steps -0.003 (t =
   -0.2); the long run +0.0094 (t = +1.2) with 66,048 weights (8%)
   fewer, x1.05 a step. Multi-query (kv=[4,1]) not run. As found:
   "quality close to multi-head attention" held, from the start (the
   paper's models were uptrained from multi-head ones; ours grouped
   from the first step). Its speed is in writing with a cache, which
   module 11 builds: here the cache would hold half as much.
2. SmolLM2-135M: its config.json beside GPT's arguments, every one the
   same (printed); 272 tensors, all BF16, 134,515,008 weights, loaded in
   1.6 s; keys and values 3 heads of 64 for 9: 11,520 numbers kept a
   token where 9 heads would keep 34,560. After "To be, or not to be,":
   ' the' 0.154, ' a' 0.122, ' is' 0.046, '\n' 0.026, ' in' 0.025 (the
   play's next word, ' that', is not among them); greedy: "To be, or not to be, the most important thing in
   life, is the fact that we are all human beings".
3. The tokenizer: 49,152 symbols, 17 special, 235 of the 256 bytes (none
   for 0x04, 0x06, 0x13, 0x14, 0x16, 0x1d, 0xc0, 0xc1, 0xf1, 0xf2, 0xf5 to
   0xff: control characters, and bytes that are never in UTF-8 or begin
   characters of planes 4 to 15), 48,900 merges, against GPT-2's 50,257,
   1, 256, 50,000. " in 2019, 1234567890": pieces ' in', ' ', '2', '0',
   '1', '9', ',', ' ', '1', ... (GPT-2: ' in', ' 2019', ',', ' 1234567890'
   cut by its merges); "x\U00040000y" is tokens [104, 218, 218, 218, 105]
   and decodes to "x" + three U+FFFD + "y" (its first byte, 0xf1, has
   no symbol). The test text: 17,912 tokens, 3.114 characters a token
   (GPT-2: 17,995, 3.099); all of Tiny Shakespeare 341,094 (GPT-2
   338,025); every one decodes back.
4. Bits on the test text (windows of 1024, each token with 64 or more
   before it, as 09.03 scores GPT-2): 4.375 a token, 1.405 a character.
   Beside: 08.04's long-run GPT 2.226 (2,731,200 weights), GPT-2 small
   1.851 (124,439,808), SmolLM2-135M 1.405 (134,515,008). Not "never
   seen": its 2 trillion tokens of web, code and education pages may
   hold the plays. Spike (scratch code, greedy, 12 tokens after the
   200 characters before a line of the test text): of five famous lines
   of The Tempest's first act ("Full fathom five thy father lies;",
   "'Hell is empty", "You taught me language;", "This island's mine,",
   "Come unto these yellow sands,") SmolLM2 continues one with four
   right words ("Of his bones are", then "the footstool'st") and one
   with one ("\nAnd"); GPT-2 none. Its validation bits are nearly its
   test bits (1.389 against 1.405; GPT-2 1.843 against 1.851), where the
   models trained here are 0.2 bits worse on test (Data above): as for
   models that did not learn the training plays in particular.
5. After "PROSPERO:\n'Tis time\nI should inform thee farther." (16 tokens,
   a speech in the middle of the test text), 40 tokens, seed 0: greedy
   "\n\n'Tis time, my dear,\nTo tell thee more of the world.\n\n'Tis time,
   my dear,\nTo tell thee more of the world.\n\n" (a loop, as 08.05 and
   09.03 found); top-k 40 "\n\nLORD OF EPHESUS:\n\nSIR ALEXANDER, (as at
   part's end of the film, his body was seen)\n'Nestle!'"; nucleus 0.95
   "\n\nNARRATOR: The Channel, which was just turning back to the Great
   Barrier, ...". Shakespeare's form for a line or two, then the web.

**10.05 Which change paid: an ablation table.** experiments/ablation.py:
rows base (08's GPT), RMSNorm, rotary, SwiGLU, grouped-query (2 key and
value heads for 4), all four; compare with every row trained alike,
validation bits of 64 (32 in the default) fixed windows logged every
`every` steps; table() prints weights, bits (spread), the difference
from the base with Welch's t, "beyond noise" (|t| >= 3) and ms a step;
curves.svg is each row's validation curve, the mean over seeds;
times.json the ms a step of every row and seed (times are never in
summary.json). The default run: 4 blocks of 4 heads, width 64, windows
of 64, 80 steps (warmup 40), 2 seeds a row; 40.9 s at load 8.6 to 10 and
44.4 s at load 12.2 to 12.7, the same digits:

    base (08)        208,320   3.721 +- 0.009156                       32.9
    RMSNorm          207,744   3.73 +- 0.01186    +0.0088 (t  +0.8)  no   39.0
    rotary           204,224   3.488 +- 0.002474  -0.2331 (t -34.8)  yes  39.8
    SwiGLU           208,144   3.832 +- 0.01812   +0.1108 (t  +7.7)  yes  30.6
    grouped-query    191,680   3.726 +- 0.0192    +0.0049 (t  +0.3)  no   33.3
    all four         186,832   3.539 +- 0.03378   -0.1819 (t  -7.3)  yes  42.9

then the recorded table and each paper's claim. What the short run can
show: rotary's early lead; that RMSNorm and grouped heads change nothing
yet; SwiGLU behind, beyond the noise, and so all four together behind
rotary alone. What it cannot: which changes still pay once the model has
trained, the long run's question, where SwiGLU turns into the largest
gain. The first default was 100 steps (40.4 s at load 7.5 but 48.4 s at
load 9.8: cut): base 3.665, RMSNorm +0.0020, rotary -0.2674 (t = -34.2),
SwiGLU +0.0499 (t = +6.4), grouped -0.0032, all four -0.2529 (t = -12.7).

The long run, recorded in experiments/recorded/ablation/ (config.json,
log.jsonl and summary.json of every row and seed; curves.svg; times.json;
output.txt, what it printed); no weights (the script saves none):

    python3 -m experiments.ablation layers=4 heads=4 width=128 context=128 batch=32 steps=2000 lr=0.002 warmup=100 every=100 held=64 seeds=3 kv_heads=2 recorded=none out=experiments/recorded

4 blocks of 4 heads of 32, width 128, windows of 128 (818,048 weights
for the base), 2000 steps of 32 windows (8.2 passes), AdamW 0.002 (08.04's
long run's), weight decay 0.1, warmup 100 then cosine, clipped to 1, no
dropout; 6 rows x 3 seeds. 2540 s by its own clock, 42 min 21 s of wall
clock (22:41:37 to 23:23:58), load 7 to 16 (two other agents' work);
each round of six rows 13 to 16 minutes. recorded=none: it writes where
the default reads, so its output leaves the recorded table out.
Bits per character on the test text (each character with 32 or more
before it):

    base (08)        818,048   2.337 +- 0.004618 (min 2.332, max 2.341)                       59.6
    RMSNorm          816,896   2.35 +- 0.007442 (min 2.345, max 2.359)  +0.0133 (t  +2.6)  no   70.6
    rotary           801,664   2.277 +- 0.01805 (min 2.263, max 2.297)  -0.0603 (t  -5.6)  yes  90.9
    SwiGLU           818,216   2.27 +- 0.009653 (min 2.259, max 2.277)  -0.0672 (t -10.9)  yes  54.5
    grouped-query    752,000   2.346 +- 0.01227 (min 2.332, max 2.354)  +0.0094 (t  +1.2)  no   62.7
    all four         734,632   2.248 +- 0.01415 (min 2.232, max 2.26)   -0.0890 (t -10.4)  yes  83.5

(the last column ms a step, the mean of 3 seeds; each seed's in
times.json, e.g. the base's 60.5, 71.3 and 46.9: the load moved them more
than the rows differ, but for rotary's and all four's.) What paid, at
this size and budget: SwiGLU (0.067 bits) and rotary positions (0.060),
both beyond the noise; RMSNorm and grouped heads did not change the
bits (+0.013 and +0.009, inside the noise) and are there for other
reasons (RMSNorm, speed where its kernel is fused, not measured here;
grouped heads, 8% fewer weights here and half the cache). All four
together are the lowest row, 0.089 below the base with 10% fewer
weights; the single changes add up to -0.105, so they do not quite add.
The paper's claims, beside: RMSNorm "comparable" (held), rotary's
faster convergence (held: 0.23 bits at 80 steps and 0.32 at 150 at
width 64, 0.06 at 2000 at width 128),
SwiGLU's 0.04 log-perplexity on a T5 base (held, at about 0.07 bits per
character, once trained 600 steps or more), grouped-query "quality
close to multi-head" (held; its speed not measured here). The test holds
rotary, SwiGLU and all four below the base by more than 0.03 and
beyond t = -3, all four the lowest, RMSNorm and grouped heads within
0.02 and |t| < 3.
Spikes, the size and the budget (what I tried; scratch code calling
compare, not in the project):
- width 64, windows of 64 (08.04's default GPT), 600 steps, 2 seeds
  (load 12.7, 211 s): base 3.015; RMSNorm +0.013 (t = +0.5); rotary
  -0.242 (t = -11.2); SwiGLU -0.044 (t = -1.9); 2 key/value heads -0.003
  (t = -0.2); all four -0.346 (t = -20.1); ms 24.4, 27.7, 30.4, 26.7,
  28.5, 35.4.
- the same at 1200 steps (load 9.4, 268 s): base 2.716; SwiGLU -0.049 (t
  = -3.5); rotary -0.158 (t = -10.5); all four -0.222 (t = -8.4).
- speed a step for the long run's candidates (load 9 to 10): width 128,
  windows of 128: 56 to 70 ms for the six rows (40 steps each); 6 blocks
  of width 192: 191 ms (base), 168 (all four), too slow for 18 runs of
  more than 900 steps in the hour; width 96: 75 and 91.
Chosen: width 128 at 2000 steps (8 passes: by 08.04's spike, a model of
this size starts to overfit after 15 to 20 passes, so no dropout), 3
seeds, about 2.3 minutes a run; the 600 and 1200-step spikes had shown
rotary's lead shrinking and SwiGLU's growing, so a longer budget was
the question worth the hour.

**Module 10's papers: what was read at the source** (2026-11-24, the PDFs
from arXiv; quotes are the papers' words, maths in ASCII; read for this
module by an agent working from the PDFs, which checked the one place
where the text extraction was unclear, the 2/3 of GLU Variants, against
the page image):
- Zhang and Sennrich, "Root Mean Square Layer Normalization", arXiv
  1910.07467v1 (NeurIPS 2019). Section 4, equation 4: abar_i = (a_i /
  RMS(a)) g_i, RMS(a) = sqrt((1/n) sum_{i=1}^n a_i^2); no bias in the
  equation (a bias b appears only in the general form, equation 5, y =
  f((Wx / RMS(a)) (.) g + b)); "Intuitively, RMSNorm simplifies LayerNorm
  by totally removing the mean statistic in Eq. (3) at the cost of
  sacrificing the invariance that mean normalization affords. When the
  mean of summed inputs is zero, RMSNorm is exactly equal to LayerNorm."
  The hypothesis (section 4): "we hypothesize that the re-scaling
  invariance is the reason for success of LayerNorm, rather than
  re-centering invariance." The claim (abstract): "RMSNorm achieves
  comparable performance against LayerNorm but reduces the running time
  by 7%~64% on different models." Where the time comes from (section 6:
  TensorFlow, PyTorch and Theano, "Unless otherwise noted, all
  speed-related statistics are measured on one TITAN X (Pascal)"): RNN
  models in TensorFlow, where "LayerNorm is slower than the Baseline by
  about 67%" and RMSNorm improves on it by about 25%; the Transformer,
  "a speedup of 7%~9%. Compared with RNNSearch, the relative cost of
  normalization is lower because there are significantly fewer
  sequential normalization operations in Transformer"; the 64% is
  pRMSNorm's (the RMS from the first p% of the numbers) on an
  order-embedding model (table 8: 12.02 s, RMSNorm 7.12, pRMSNorm 4.34).
  Section 7: "Actual speed improvements depend on the framework,
  hardware, neural network architecture and relative computational
  cost of other components". Table 4 (Transformer base, WMT14
  English-German, SacreBLEU, seconds per 1,000 steps on a V100):
  LayerNorm 26.6 / 27.7, 248 s; RMSNorm 26.8 / 27.7, 231 s (6.9%).
  Not read: the other tasks' tables beyond tables 2, 4 and 8.
- Su et al., "RoFormer: Enhanced Transformer with Rotary Position
  Embedding", arXiv 2104.09864v5. Section 3.1,
  equation 11, the goal: <f_q(x_m, m), f_k(x_n, n)> = g(x_m, x_n, m - n);
  3.2.1, the 2D case, equations 12 and 13 ("simply rotate the
  affine-transformed word embedding vector by amount of angle multiples
  of its position index"); 3.2.2, equations 14 and 15: "we divide the
  d-dimension space into d/2 sub-spaces", a block-diagonal R^d_{Theta,m}
  whose block j turns coordinates 2j - 1 and 2j (neighbours), Theta =
  {theta_i = 10000^(-2(i-1)/d), i in [1, ..., d/2]} (section 3.3 writes
  10000^(-2i/d), 0-based as ours); equation 16, q_m^T k_n = x^T W_q
  R^d_{Theta,n-m} W_k x_n; 3.4.2, equation 34, the efficient form, x
  times (cos m theta_1, cos m theta_1, cos m theta_2, ...) plus (-x2, x1,
  -x4, x3, ...) times the sines (our neighbours()); "Note that R^d_Theta
  is an orthogonal matrix" and (3.3) RoPE "keeps the norm of hidden
  representations unchanged". Claims: abstract, "RoPE enables valuable
  properties, including the flexibility of sequence length, decaying
  inter-token dependency with increasing relative distances, and the
  capability of equipping the linear self-attention with relative
  position encoding"; 4.2.3, "Compare to the vanilla BERT, RoFormer
  experiences faster convergence" (a figure, no numbers); table 1, WMT14
  English-German BLEU 27.3 (Transformer base) against 27.5; table 5
  (CAIL2019-SCM, test accuracy), BERT-512 67.77%, RoFormer-512 68.29%,
  RoFormer-1024 69.79%; 4.5.5, its limits: "there lacks of thorough
  explanations on why it converges faster than baseline models". The
  paper has no section that measures "flexibility of sequence length"
  beyond the 1024-token row.
- Shazeer, "GLU Variants Improve Transformer", arXiv 2002.05202v1.
  Swish_beta(x) = x sigma(beta x); SwiGLU(x, W, V, b, c, beta) =
  Swish_beta(xW + b) (x) (xV + c) (equation 5); "we omit the bias terms":
  FFN_SwiGLU(x, W, V, W2) = (Swish_1(xW) (x) xV) W2 (equation 6). Section
  2: "All of these layers have three weight matrices, as opposed to two
  for the original FFN. To keep the number of parameters and the amount
  of computation constant, we reduce the number of hidden units d_ff
  (the second dimension of W and V and the first dimension of W2) by a
  factor of 2/3"; 3.1, d_ff 3072 against 2048 for d_model 768; the
  set-up, a T5 encoder and decoder of 12 layers each, d_model 768, 12
  heads, 524,288 steps on C4, batches of 128 examples of 512 input and 114
  output tokens. Table 1 (heldout log-perplexity, 65,536 steps with the
  sd of four runs / 524,288 steps): FFN_ReLU 1.997 (0.005) / 1.677,
  FFN_GELU 1.983 (0.005) / 1.679, FFN_Swish 1.994 (0.003) / 1.683,
  FFN_GEGLU 1.942 (0.004) / 1.633, FFN_SwiGLU 1.944 (0.010) / 1.636.
  Section 4: "We offer no explanation as to why these architectures seem
  to work; we attribute their success, as all else, to divine
  benevolence." Its fine-tuning tables (GLUE, SuperGLUE, SQuAD) not read.
- Dauphin et al., "Language Modeling with Gated Convolutional Networks",
  arXiv 1612.08083v3: equation 1, h_l(X) = (X *
  W + b) (x) sigma(X * V + c), "We dub this gating mechanism Gated Linear
  Units (GLU)"; section 1, "Our gated linear units reduce the vanishing
  gradient problem for deep architectures by providing a linear path for
  the gradients while retaining non-linear capabilities"; section 3, the
  GLU's gradient "has a path grad X (x) sigma(X) without downscaling for
  the activated gating units in sigma(X). This can be thought of as a
  multiplicative skip connection which helps gradients flow through the
  layers." Its experiments not read.
- Ainslie et al., "GQA: Training Generalized Multi-Query Transformer
  Models from Multi-Head Checkpoints", arXiv 2305.13245v3. Section 2.2: "Grouped-query attention
  divides query heads into G groups, each of which shares a single key
  head and value head. GQA-G refers to grouped-query with G groups.
  GQA-1, with a single group and therefore single key and value head, is
  equivalent to MQA, while GQA-H, with groups equal to number of heads,
  is equivalent to MHA." Why (section 1): "Autoregressive decoder
  inference is a severe bottleneck for Transformer models due to the
  memory bandwidth overhead from loading decoder weights and all
  attention keys and values at every decoding step"; 2.2, "reducing the
  size of the key-value cache and therefore amount of data that needs to
  be loaded by a factor of H". The claim (abstract): "We show that
  uptrained GQA achieves quality close to multi-head attention with
  comparable speed to MQA"; the uptraining: "using 5% of original
  pre-training compute", key and value heads "mean pooled" from the
  multi-head checkpoint (2.1). Table 1 (T5, the XXL MQA and GQA uptrained
  5%; inference time a sample in s, average quality): MHA-Large 0.37,
  46.0; MHA-XXL 1.51, 47.2; MQA-XXL 0.24, 46.6; GQA-8-XXL 0.28, 47.1. Ours
  trains grouped heads from the start, not uptrained: the paper's
  set-up is not run.
- Touvron et al., "LLaMA: Open and Efficient Foundation Language Models",
  arXiv 2302.13971v1, section 2.2, the three bullets: "Pre-normalization
  [GPT3]. ... We use the RMSNorm normalizing function, introduced by
  Zhang and Sennrich (2019)."; "SwiGLU activation function [PaLM]. We
  replace the ReLU non-linearity by the SwiGLU activation function,
  introduced by Shazeer (2020) to improve the performance. We use a
  dimension of 2/3 4d instead of 4d as in PaLM."; "Rotary Embeddings
  [GPTNeo]. We remove the absolute positional embeddings, and instead,
  add rotary positional embeddings (RoPE), introduced by Su et al.
  (2021), at each layer of the network." Table 2's smallest row: 6.7B,
  dimension 4096, 32 heads, 32 layers, lr 3.0e-4, batch 4M tokens, 1.0T
  tokens. Touvron et al., "Llama 2", arXiv 2307.09288v2: "adopted
  grouped-query attention (Ainslie et al., 2023)" (section 1); table 1's
  caption, "Bigger models - 34B and 70B - use Grouped-Query Attention
  (GQA) for improved inference scalability"; appendix A.2.1, "the GQA
  variant performs comparably to the MHA baseline on most evaluation
  tasks and is better than the MQA variant on average". Its numbers for
  that ablation not read.
- Allal et al., "SmolLM2: When Smol Goes Big", arXiv 2502.02737v1:
  section 6, SmolLM2-135M "trained on 2T tokens", "These models share the
  same architecture as SmolLM2-1.7B but use Grouped Query Attention
  (GQA)"; section 4.1, "the tokenizer from Allal et al. (2024), which has
  a vocabulary size of 49,152 tokens"; appendix A's table 6 is the 1.7B
  (tied embedding, RoPE theta 10,000, SwiGLU); the 135M's own sizes are
  only in its model card and config.json ("More details about
  SmolLM2-360M and 135M can be found in their respective model cards").
- The model card (README.md at the pinned commit, read whole):
  `license: apache-2.0` in its metadata, a License section linking the
  Apache License 2.0; "The 135M model was trained on 2 trillion tokens
  using a diverse dataset combination: FineWeb-Edu, DCLM, The Stack";
  nanotron, 64 H100s, bfloat16. config.json, every field: in
  models/smollm.py's docstring, and printed by 10.04's part 2.
- The reference code, read where it is installed (transformers 4.57.6,
  models/llama/modeling_llama.py and modeling_rope_utils.py):
  LlamaRMSNorm (x in float32, x * rsqrt(mean(x^2) + eps), times weight;
  no bias), LlamaRotaryEmbedding (inv_freq = 1 / base^(arange(0, d, 2) /
  d) in float32; the angles a matrix product, then cat(freqs, freqs), cos
  and sin, "Force float32" with autocast off, cast to the input's type
  at the end), rotate_half (cat(-x2, x1): numbers i and i + d / 2 make a
  pair), apply_rotary_pos_emb, LlamaMLP (down(act(gate(x)) * up(x))),
  repeat_kv ("the equivalent of torch.repeat_interleave(x, dim=1,
  repeats=n_rep)"), eager_attention_forward (scores times head_dim^-0.5,
  the mask added, softmax in float32), LlamaDecoderLayer (pre-norm: x +
  attention(input_layernorm(x)), then x + mlp(post_attention_layernorm
  (x))). SmolLM2's config.json says "rope_interleaved": false, a nanotron
  field: its weights are for the half-split pairing, which is ours.
- tokenizers v0.22.2 (github, the tag), read for 10.04's tokenizer:
  pre_tokenizers/digits.rs, `normalized.split(char::is_numeric,
  SplitDelimiterBehavior::Isolated)` with individual_digits (Rust's
  is_numeric is the categories Nd, Nl and No: every number, not only
  0-9); pre_tokenizers/byte_level.rs, the regex GPT-2's encoder.py has,
  word for word, applied when use_regex is true.

**Departures from the design, and why** (each said above where it
belongs):
- The defaults of 10.01 to 10.04 train 150 steps, not 08.04's 300: two
  models of 3 seeds in under a minute on a machine at load 8 to 13 (at
  200 steps 10.01's default took 42.9 s at load 6 to 9, so 300 would pass
  a minute). So their base row is not 08.04's 3.332 (that was 300 steps,
  2 seeds); at 150 steps the base GPT scores 3.563 (3 seeds). Longer
  comparisons are the ablation's long run and its spikes.
- 10.04's default compares the heads over 2 seeds, not 3 (45 s at load
  6.5 with 3; 33 to 37 s with 2), and 10.05's default trains 80 steps,
  not the first 100 (48 s at load 9.8; 41 to 44 s with 80).
- RMSNorm has no bias (the paper's equation 4, transformers' and
  torch.nn.RMSNorm's), so the RMSNorm GPT has (2L + 1) x width fewer
  weights than layer norm's with bias=True: 576 of 208,320 at the
  default, said in the run.
- SwiGLU's inner width is 8 x width // 3, rounded down: 170 at width 64
  (two thirds of 256 is 170.7), 176 weights fewer over 4 blocks with
  biases (-44 a block), said in the run; exact at SmolLM2's 576 (1536,
  without biases the same count as the GELU MLP's, which the run and
  the test show), and at any width divisible by 3 the matrices are
  equal and only the biases differ.
- Rotary pairs numbers i and i + d / 2, transformers' and SmolLM2's
  convention ("rope_interleaved": false), not the paper's neighbours.
  The two are the same turning with the projection's rows in another
  order: 10.02's run and test show the scores equal to 1e-12 once the
  numbers are reordered, and experiments/rotary.py has the paper's form
  (neighbours) as a region.
- 10.04's grouped-query attention has no region: it is four @from 10.04
  blocks in SelfAttention (the key and value widths, the check, the
  view by -1, the repeat). The lesson's regions are lab/safetensors.py's
  bfloat16, models/smollm.py's from_smollm and load, tokens/smollm.py's
  split and Tokenizer; experiments/smollm.py has none (FILES_FROM).
- 10.04's default compares 4 key and value heads with 2 (kv=[4,2]), not
  with 1 as well: a third row did not fit beside SmolLM2 in a minute.
  kv=[4,2,1] runs multi-query too (not measured here).
- tokens/smollm.py reads tokenizer.json, not vocab.json and merges.txt as
  tokens/gpt2.py reads GPT-2's: the special symbols and the steps that
  cut a text are only in tokenizer.json (the repository's vocab.json and
  merges.txt hold the same symbols and merges: checked equal). It refuses
  a file that cuts text any other way. Its Tokenizer is new code, not
  tokens/gpt2.py's: GPT-2's checks that the k-th merge makes 256 + k,
  and SmolLM2's k-th makes 252 + k (17 specials and 235 bytes before
  them); byte_symbols, classes, split (GPT-2's pattern) and 09.01's merge
  loop and decode are reused.
- The fetch has four files: config.json (10.04 prints it beside GPT's
  arguments, and the test's reference reads it), tokenizer.json,
  tokenizer_config.json (only the test's reference, transformers'
  AutoTokenizer, reads it) and model.safetensors.
- experiments/language.py's compare warms each variant up with one
  untimed AdamW step before the timed runs: a process's first optimiser
  step costs about 0.4 s here (measured: 74 to 79 ms a step over 6 steps
  for the first run of a process, 2.5 to 2.9 after; with an optimiser
  step first, 3.2 to 3.9), which put 2 to 3 ms a step on the first
  variant's first seed at 150 steps. The bits are unchanged (the seed is
  set again before each model).

## For module 11: what module 10 leaves in models/gpt.py

- `self_attend(q, k, v, mask, scale)` is unchanged and still the one
  function to swap. Everything module 10 added happens before it, in
  `SelfAttention.qkv`: q and k are already turned by Rotary (when the
  model has rotary positions) and k and v are already repeated from
  kv_heads to heads (repeat_interleave on dim 1: query head h reads key
  head h // (heads // kv_heads), as transformers' repeat_kv). So
  F.scaled_dot_product_attention(q, k, v, is_causal=True) takes qkv's
  output as self_attend does (its default scale is 1 / sqrt(d), ours).
  With grouped heads it can also take k and v before the repeat with
  enable_gqa=True (torch 2.10 has it; the 10.04 test compares the two at
  1e-12): if module 11 moves the repeat there, attention_maps (which
  calls a.qkv and self_attend) must get the repeat some other way.
- A cache of keys and values for generate: keep each block's k and v as
  qkv makes them, turned and before the repeat (kv_heads of them: that
  is the point of grouped heads, a third of the numbers for SmolLM2).
  New tokens must be turned for their own places: Rotary.forward(x,
  start) takes the place of x's first vector, and qkv does not pass one
  yet (it turns from place 0): give qkv a `start` and pass it to both
  turns. The mask is no longer square: T new queries at places start to
  start + T - 1 see start + T keys; causal_mask(T) and is_causal assume
  as many queries as keys (PyTorch's is_causal aligns the triangle at the
  top left, which is wrong for T new queries after a cache unless T is
  1). transformers
  caches post-rotary keys too (LlamaAttention: apply_rotary_pos_emb, then
  past_key_values.update).
- Rotary computes its angles, cos and sin at every call: twice a block,
  every forward. At 08.04's size (width 64, 4 heads of 16) a training
  step of the rotary GPT took 18 to 30% longer than the learned-position
  GPT's (10.02: 30.9 against 26.1 ms; the 1200-step spike 31.6 against
  24.6), and at the long run's (width 128, windows of 128) 52% longer
  (90.9 against 59.6 ms, a busy machine). The arithmetic is small; the cost is a
  dozen small operations a call (arange, pow, mul, repeat, cos, sin, cat,
  ...), which a table made once per length would remove. A candidate for
  11.02's profile and 11.06's "one more optimisation".
- RMSNorm is written out (pow, mean, rsqrt, two multiplies) and is
  slower than nn.LayerNorm's one fused kernel on this CPU (10.01: alone
  2.3 to 3.0 times nn.LayerNorm's time; a whole step 11 to 18% slower);
  torch.nn.RMSNorm is no faster here (torch 2.10, CPU). A fused
  F.rms_norm, where torch has one for the device, is the same numbers.
- Numbers to keep the same: SmolLM2-135M's logits equal transformers'
  exactly in float32 with eager attention (the 10.04 test asserts 1e-4
  of each logit and prints the largest difference, 0 here); with
  transformers' sdpa attention 7.8e-5 apart; in float64 2.4e-5 apart,
  because transformers computes the rotary angles in float32 whatever
  the model's type. Rotary's cos and sin are taken of the angles each
  repeated twice ((T, d), not (T, d / 2) then repeated): on this CPU cos
  of the two layouts differs in the last bit for some lengths (from 512
  places), and the repeated layout is what transformers computes; the
  10.02 test holds Rotary equal to transformers' turning bit for bit at
  16 and 600 places.

## For modules 12 and 13: the variants, SmolLM2 and its tokenizer

**Each variant** is GPT with one argument (all compose):

    GPT(vocab, context, layers, heads, width, norm="rms")                 # 10.01: RMSNorm everywhere
    GPT(vocab, context, layers, heads, width, positions="rotary")         # 10.02: base=10000.0 by default
    GPT(vocab, context, layers, heads, width, mlp="swiglu")               # 10.03: hidden = 8 * width // 3
    GPT(vocab, context, layers, heads, width, kv_heads=2)                 # 10.04: heads % kv_heads == 0
    experiments.language.compare(variants, common, cfg, dev, ids, test)   # train, time and score several alike

compare's cfg needs steps, batch, context, lr, warmup, weight_decay,
clip, every, seeds, out and name (lab.config gives the last two);
variants is {name: GPT's arguments}, common the arguments they share;
it returns each variant's bits, ms a step, weights and models by seed
and writes a run for each (label = the name). 13.01 to 13.04 can use it
as it is for "the same budget for both".

**SmolLM2-135M and its tokenizer in three lines**, from the project's top,
once `python3 -m data.fetch smollm2` has run:

    import torch; from models import smollm as M; from tokens import smollm as T
    model, tok = M.load(torch.device("cpu")), T.load()       # GPT(**M.CONFIG) in eval mode, float32; the tokenizer
    scores = model(torch.tensor([tok.encode("To be, or not to be,")]))   # (1, n, 49152); tok.decode(ids)

model is models/gpt.py's GPT (vocab 49152, context 8192, 30 blocks of 9
query heads on 3 key and value heads of 64, width 576, SwiGLU of 1536,
RMSNorm, rotary base 100000, no biases, tied output): generate,
window_bits, save and load (experiments/language.py) all work on it
(save writes float32: 538 MB). tok.encode treats special symbols' text
as text; T.END is 0, <|endoftext|>; tok.specials maps each special's
text to its id: <|im_start|> is 1, <|im_end|> 2, the chat template's
markers (SmolLM2-135M is the base model, not the instruct one, so it
has never been trained on a chat in them: 12.03 would teach it).
tok.first[b] is None for the 21 bytes with no symbol (a text with one
of them does not decode back: the reference does the same).
Fine-tuning it (12): the training step below, AdamW's two moments for
134.5M weights (another 1.1 GB in float32).

**SmolLM2-135M's files, checked before they were pinned** (2026-11-24):
the repository's commit 93efa2f097d58c2a74874c7e644dbc9b0cee75a2 (its
main on that day, last changed 2025-02-06; Hugging Face's API, models/
HuggingFaceTB/SmolLM2-135M/revision/main and /tree/<commit>, lists ten
files: .gitattributes, README.md, config.json, generation_config.json,
merges.txt, model.safetensors, special_tokens_map.json, tokenizer.json,
tokenizer_config.json, vocab.json). model.safetensors is a Git LFS file
of 269,060,552 bytes whose LFS oid, its SHA-256, is
80521b40281d6ce74e35c9282c22539e75aa0ac8578892b2a59955ef78d55da1 (the
X-Linked-ETag module 09's notes saw): fetched in 32 s, its SHA-256 the
same. The small
files are plain git blobs: each one's git blob SHA-1 (sha1 of "blob
<size>\0" and the bytes) equals the tree's oid, then its SHA-256 was
computed and pinned (data/fetch.py has all four). The header (30,528
bytes, metadata {"format": "pt"}): 272 tensors, every one BF16, names
model.embed_tokens.weight [49152, 576], model.layers.i.{input_layernorm,
post_attention_layernorm}.weight [576], .self_attn.{q,o}_proj.weight
[576, 576], .self_attn.{k,v}_proj.weight [192, 576], .mlp.{gate,up}_proj
.weight [1536, 576], .mlp.down_proj.weight [576, 1536], model.norm.weight
[576]; no lm_head (tied), no biases: 134,515,008 weights. Read by
lab/safetensors.py in 0.1 s from the page cache; every tensor equals the
safetensors library's (safetensors.torch, bfloat16, .float()), exactly.

**Fetching** (data/fetch.py; checked against the pinned size and
SHA-256 before it is kept; resumed with an HTTP Range request if
dropped; a generic User-Agent, no account, no token):

    python3 -m data.fetch smollm2       config.json 704, tokenizer.json 2,104,556, tokenizer_config.json 3,658,
                                        model.safetensors 269,060,552 bytes (271,169,470 in all)
                                        https://huggingface.co/HuggingFaceTB/SmolLM2-135M/resolve/93efa2f097d58c2a74874c7e644dbc9b0cee75a2/
                                        32 s here

**Speeds on this CPU** (SmolLM2-135M in float32, 10 threads, load about
10, no cache of keys and values):
- loading (models/smollm.load: the file, widening, GPT's random start,
  load_state_dict): 1.6 s, peak 1.4 GB.
- the tokenizer: all of Tiny Shakespeare (1.1 MB) in 0.42 s with its
  cache, 341,094 tokens (transformers' fast tokenizer 0.33 s).
- forward, scoring: 1 x 1024 tokens 0.36 s (2,800 tokens a second); 4 x
  256 0.19 s (5,300); 16 x 64 0.18 s (5,700); 1 x 64 0.05 s. Scoring the
  test text (17,912 tokens, windows of 1024, warm 64) is part of 10.04's
  33 s.
- generating (language.generate, a whole forward a step): 1 row, 64
  tokens after 32: 3.1 s, 20 tokens a second (49 ms a step); 8 rows: 8.7
  s, 59 a second (136 ms a step); 1 row, 32 after 512: 5.5 s, 5.8 a
  second (172 ms a step). Module 11's cache is what would change this.
- a training step (AdamW, float32, cross-entropy on the next token): 4 x
  256 tokens 1.0 s, 8 x 128 0.99 s; the process's peak memory 5.2 GB (the
  weights, their gradients and AdamW's two moments: 4 x 538 MB, and the
  activations). An hour of CPU is about 3,600 such steps, 3.7 million
  tokens: enough for 12's fine-tuning on a small labelled set, not for
  pretraining.
- the variants at 08.04's size (width 64, windows of 64): 20 to 35 ms a
  step, rotary and all four the slowest (10.01 to 10.05 above).

**Module 10's tests** (tests/1001_ to 1005_, each its exact and
differential checks first, in a fresh python, then its experiment):
- 1001: RMSNorm against the formula (support.rms_norm) and
  torch.nn.RMSNorm (1e-12, float64), gradcheck, equal to layer norm on
  centred vectors; the written-out layer norm against nn.LayerNorm; the
  default GPT built draw for draw as one with norm="layer"; GPT(norm=
  "rms"): every norm an RMSNorm, (2L + 1) W weights fewer, the names,
  against support.gpt10_numpy (1e-10), causal; compare: two variants of
  the same settings give the same bits whatever their turn, a third
  differs, every run written; centring's first value against a direct
  computation; uncentred leaves its model alone, changes nothing on
  centred vectors and does change the scores; norm_times. Then rmsnorm
  (the default, 3 seeds): RMSNorm within 0.05 bits of layer norm, the
  layer-norm model's norms reading vectors with |mean| / rms under 0.2,
  its bits within 0.01 without the mean step; a tiny run twice, byte
  for byte.
- 1002: Rotary against the 2 x 2 turns written out (support.rotate_numpy,
  bases 10000 and 100000, 1e-12), place 0 unturned, scores unchanged when
  both move by 1, 5, 77 or 500 places (1e-12), lengths kept (1e-14), the
  paper's neighbours reordered (1e-12); against transformers'
  LlamaRotaryEmbedding and apply_rotary_pos_emb bit for bit (float32, 16
  and 600 places); GPT(positions="rotary"): no table, context x W weights
  fewer, against gpt10_numpy (1e-10), causal, reads 4 x context,
  attention_maps rebuilds block 1 (1e-12). Then rotary (the default):
  rotary more than 0.1 bits below learned, the ValueError, worse past the
  trained length by 0.05 or more, the shift line under 1e-9; a tiny run
  twice.
- 1003: SwiGLU against the formula (1e-12), F.silu against x sigmoid(x)
  (1e-15), its weight count 3 W h + (2h + W) for three sizes, equal to the
  MLP's at 576 / 1536 without biases; against transformers' LlamaMLP on
  the same weights (1e-12); GPT(mlp="swiglu"): shapes, the count, the
  start (gate sd 0.02, down 0.02 / sqrt(2L), biases 0), hidden=, against
  gpt10_numpy (1e-10); gates against a direct computation. Then swiglu:
  within 0.1 bits of the GELU MLP and below 3.8, -176 weights, the 576
  line, the gates' shares in [0, 1]; a tiny run twice.
- 1004: SelfAttention(12, heads=6, kv_heads=2) against support's loops
  (1e-12), its repeated keys, against F.scaled_dot_product_attention with
  enable_gqa (1e-12), against full heads whose key and value rows repeat
  each group's (1e-12), 6 on 4 refused; GPT(kv_heads=1): its count,
  against gpt10_numpy (1e-10), causal, attention_maps; bfloat16 against
  PyTorch on all 65,536 bit patterns (as float32 bits, NaNs included);
  load_file on a file the safetensors library wrote with a BF16, an F32
  and an I64 tensor; split against the tokenizers library's Digits and
  ByteLevel pre-tokenizers, built in the test as tokenizer.json names
  them, on 09.02's corpus, 2,000 random strings and three more (every
  piece equal, as byte symbols); a tokenizer.json written by the test
  (specials, a byte missing, three merges): ids, decode, the missing byte
  left out, merges out of order and another pre-tokenizer refused;
  from_smollm with transformers' LlamaForCausalLM (random weights, 2
  blocks, 6 heads on 2, rotary base 100000, tied, no biases) at 1e-5 in
  float32 and float64; without kv_heads, a size mismatch. Then
  T.need(t, "smollm2") (without the files: "missing:" and the fetch
  command, as 09.03), and with_data: SmolLM2-135M's logits against
  transformers' (AutoModelForCausalLM from the cache folder,
  local_files_only, eager, float32) on 1,024 tokens of Tiny Shakespeare
  and 4 rows of 64 random tokens (1e-4 of each logit; printed: 0 and 0);
  ids against transformers' AutoTokenizer (GPT2TokenizerFast from the same
  folder) on all of Tiny Shakespeare, 09.02's corpus, 3,000 random strings
  and three more, every string decoding back unless it holds a byte with
  no symbol (53 of 3,296 here). Then smollm (the default): grouped within
  0.1 bits of full heads, 16,640 weights fewer, SmolLM2 below 1.8 bits
  per character with 134,515,008 weights and over 17,000 tokens, its
  config confirmed, 272 BF16 tensors, the round trip; a tiny run twice.
- 1005: table against direct numbers (the difference, t, yes / no, the
  times); variants' names and labels; the recorded long run's files
  (every row and seed with the same settings, the validation curve in
  every log, the summaries, curves.svg, times.json, output.txt, no
  weights) and its result (rotary, SwiGLU and all four below the base
  by more than 0.03 and t below -3, all four the lowest, RMSNorm and
  grouped heads within 0.02 and |t| under 3); then ablation (the default):
  every row 2 seeds, rotary more than 0.05 below the base, the recorded
  table and the claims printed, curves and times written; a tiny run
  twice; LEARN_RERUN_LONG=1 runs the long run again.

With module 10 (two other agents' work going, load 8 to 12): `./learn
test research` 49 tests, all pass, 19 min 12 s; module 10's five 4 min 9
s (10.01 51.9 s, 10.02 47.4, 10.03 42.3, 10.04 57.4, 10.05 50.3), each
with its experiment's default run and a tiny run twice. 10.04's printed
lines: the largest difference from transformers' logits 0 on 1,024 tokens
of Tiny Shakespeare (logits up to 40) and on 4 rows of 64 random tokens
(up to 38); the same ids as GPT2TokenizerFast on Tiny Shakespeare
(341,094 tokens) and 3,296 awkward strings, 53 of which do not decode
back, each holding a byte SmolLM2 has no symbol for. The long run is
rerun only with LEARN_RERUN_LONG=1 (about 45 minutes).
10.05's test again after its default was cut to 80 steps: pass, 54.9 s.
`./learn check-skeleton research` ok, 58 s (49 lessons, each fails at
its stub: 10.01 at RMSNorm, 10.02 at Rotary, 10.03 at SwiGLU, 10.04 at
bfloat16, 10.05 at table). `./learn check-timeline research` ok, 4 min
59 s at load 9 to 12; the project has 195 files at 10.01, 196 at 10.02,
197 at 10.03, 200 at 10.04 and 258 at 10.05 (57 of them the recorded
run); 06.04 still 98, 07.02 145, 08.04 170, 08.05 171, 09.04 194.
`./learn selftest` ok (269 tests). `./learn check` reports exactly the
"test has no lesson doc" lines of the lessons not yet written (09.0N,
whose pages another agent is writing, and 10.0N); nothing else.

**For the harness and the lessons agent (module 10).**
- No harness change. The glob order once more: track.py's module-10
  part puts "experiments/recorded/ablation/*" first in FILES_FROM.
  needs=: 10.01, 10.02, 10.03 and 10.05 need "torch" (the text ships);
  10.04 needs "torch smollm2" (TOOLS["smollm2"], DATASET_FILES, need()).
  check-timeline runs smollm only where SmolLM2's files are in the
  cache (DATASET_OF) and expects its "smollm2 is missing" line
  elsewhere; its part 1 (the heads) runs before the check, so the
  missing line comes after part 1's table.
- Signatures that grow over several lessons: each new argument is a
  continuation line with a one-line `# @from 10.0N` marker, and the
  closing `):` stands on a line of its own; the lesson that first splits
  the signature (10.01 for Block and GPT, 10.02 for SelfAttention) nests
  its @from block inside the earlier lesson's body (kilo.c's pattern),
  so 08.0N's one-line signature is still an @else part. Checked with
  harness/timeline.py: the file at 08.01 to 09.04 is exactly as before.
- Lead-in names that match more than one thing (they match without
  case): `rmsnorm` (experiments/rmsnorm.py) and `RMSNorm` (the class);
  `rotary` (experiments/rotary.py) and `Rotary`; `swiglu` and `SwiGLU`;
  `smollm` (models/smollm.py, tokens/smollm.py, experiments/smollm.py).
  Ordinary-word region titles: compare (language.py 10.01), table
  (ablation.py 10.05), gates (swiglu.py 10.03), centring, uncentred,
  neighbours, split (tokens/gpt2.py 09.02 and tokens/smollm.py 10.04),
  load (four files), Tokenizer (09.02 and 10.04). No lesson has two
  regions of one name.
- tokens/smollm.py's load is not a region (models/smollm.py's load is,
  in the same lesson).

**The lessons (written 2026-11-25, after the code).** Five lessons in
lessons/10-todays-architecture/, the module page, 19 figures
(art/research/figs10.py, every one from a run of the project, the fetched
files or the recorded ablation, each checked against what its run
printed), the five maps (archmap.py: the piece "10" from 10.01, the
language experiments' label "modules 07-10", so every map was drawn
again), and the cover (research_art.py's res_modern, its numbers read from
recorded/ablation/ and 10.04's page and asserted). Measured on a busy
machine (three other agents training, load 11 to 20); the digits are the
ones above, the times are not to be quoted from here but from a quiet
pass:
- The default runs as the pages show them: rmsnorm 42 s (load 12), rotary
  57 s (15), swiglu 51 s (15), smollm 66 s (20), ablation 64 s (17).
  Times in them: RMSNorm alone 0.64 and 0.67 of the written-out layer
  norm, 2.69 and 2.45 times nn.LayerNorm; a step x1.203 (the figure's own
  run x1.25); rotary x1.259; SwiGLU x0.887; 2 key/value heads x1.106;
  SmolLM2 loaded in 1.9 s. The pages state NOTES' ranges above, not these.
- 10.03's longer runs, made for its figure and quoted on the page
  (experiments.swiglu steps=600 and steps=1200, 3 seeds, the defaults
  otherwise): 600 steps GELU 3.020, SwiGLU 2.962, -0.0580 (t = -3.4), 199
  s; 1200 steps 2.725 against 2.673, -0.0529 (t = -3.9), 366 s. (The
  2-seed spikes above: -0.044 and -0.049.) The sign turns between 150 and
  600 steps at width 64.
- The recorded run's validation curves (every 100 steps, mean of 3
  seeds, less the base): SwiGLU -0.043 at step 100, -0.07 to -0.15 from
  300 on, ahead at every logged step but 0 (+0.05 at the start, before
  training). So at width 128, rate 0.002, warmup 100, SwiGLU is never
  behind: the slow start is the page's setting's (width 64, rate 0.003,
  warmup 50). 10.03 says so beside the reason offered. Rotary: -0.38 at
  100, -0.489 at 200, -0.095 at 1999. RMSNorm and grouped heads within
  0.03 of the base throughout.
- Break it, each run once: 10.01, RMSNorm's mean over dim -2 (the window's
  positions): part 1 1.88 from nn.RMSNorm; RMSNorm 3.456, -0.1069 (t =
  -10.3): a false win, the norm reading later positions. 10.02, turning
  the queries only: 3.544, -0.0194 (t = -6.3); past the length 3.534 /
  3.644 and 3.525 / 3.646 / 3.808; the offset line unchanged. 10.03,
  down(up(x)): 3.568, +0.0050 (t = +1.1), part 3 prints no blocks (the
  gate layer is never called). Also tried, not on the page: the gate
  without SiLU (Shazeer's bilinear), 3.571, +0.0076 (t = +1.8). 10.04,
  repeat instead of repeat_interleave: 2 key/value heads 3.574 (+0.0088,
  t = +2.6); SmolLM2 18.605 bits a token, 5.975 a character, its likeliest
  tokens byte pieces of accented letters. 10.05, the line at 2: the long
  run's RMSNorm row (t = +2.6) becomes "yes"; the short run unchanged.
- 10.04's page compares with transformers in a session of its own
  (needs="torch smollm2 transformers"; track.py's module-10 part gains
  TOOLS["transformers"], as 09.02's tiktoken): the same ids on all of Tiny
  Shakespeare (341,094 tokens), logits of 1,024 tokens up to 40.5, the
  largest difference 0.0; 16 s. transformers writes warnings and a
  protobuf AttributeError to stderr here, so the page's command ends in
  2> /dev/null.
- Fixed in the code: experiments/smollm.py printed the decoded "x" +
  U+FFFD x 3 + "y" with !r, which keeps U+FFFD as itself (it is
  printable): the page could not show it in ASCII. It prints ascii() of
  it now, 'x\ufffd\ufffd\ufffdy'; nothing else changed.
- Read at the source for the pages, beyond the papers above: GLU Variants
  whole (pdftotext): table 1's other rows, FFN_GLU 1.982 (0.006) / 1.663,
  FFN_Bilinear 1.960 (0.005) / 1.648, FFN_ReGLU 1.953 (0.003) / 1.645; its
  caption, "All models are matched for parameters and computation";
  section 3.1, d_ff 3072, 2048 for the GLU variants. RoFormer v5:
  section 4.2 ("we replace the original sinusoidal position encoding of
  BERT with our RoPE"; bert-base-uncased, batch 64, length 512, 100k
  steps, AdamW at 1e-5); 4.2.3 points at figure 3, left (MLM loss, no
  table); 4.5.5's two limits; table 5 (BERT-512 67.77%, WoBERT-512
  68.10%, RoFormer-512 68.29%, RoFormer-1024 69.79% on test). The GQA
  abstract page: Ainslie, Lee-Thorp, de Jong, Zemlyanskiy, Lebron (with an
  accent), Sanghai; v1 22 May 2023, v3 23 Dec 2023. cs336.stanford.edu:
  lecture 3 "Architectures, hyperparameters", assignment 1 "Implement all
  of the components (tokenizer, model architecture, optimizer) necessary
  to train a standard Transformer"; it names none of the four changes.
- ablation.py's CLAIMS said rotary was faster than "BERT's learned
  positions"; the paper's section 4.2 says it replaced BERT's "sinusoidal
  position encoding" (bert-base-uncased's positions are in fact learned).
  The planner changed the claim to "than BERT in pre-training" in the
  script, in the recorded output.txt and in 10.05's transcript (the same
  words, wrapped as the script wraps them; no number moved). The page
  quotes the paper's own words.
- For whoever edits these pages: a file-writing tool may turn a
  backslash-u escape into the character itself (it did, once, in 10.04's
  transcript); check with LC_ALL=C grep -nP '[^\x00-\x7F]'. verify
  refuses the words "reference code" in a page (it reads them as talk of
  the track's own reference solution). In a trimmed session, "line N"
  counts the block's own lines, not the program's.

## Module 14: reproduce a paper, grokking

Built by one agent on 2026-11-24, on the reference machine above (Apple M4
Pro, Python 3.12.7, numpy 2.4.3, PyTorch 2.10.0, 10 threads by default),
shared all the while with another agent's training (load 4 to 14). Every
time below says its load.

### The files

```
data/modular.py          14.01   SYMBOLS, divide, OPERATIONS, equations, tokens, split, names: the paper's data
experiments/predictions.py 14.01 PAPER, NANDA, SETUP, Claim, CLAIMS, verdict: the claims as predictions (no main)
experiments/claims.py    14.01   memoriser; prints SETUP, CLAIMS and the baselines
experiments/arithmetic.py 14.02  log_steps, score, train: the loop module 14 shares (as language.py is 08's)
                         14.03   weight_norm, first_step, milestones; train logs the norm (@from)
                         14.04   train's stop (@from); scaled_start, read_seeds, read_runs, median_steps
experiments/grokking.py  14.02   the experiment from the text (no region: FILES_FROM); 14.03's part 3 (@from)
experiments/ablations.py 14.04   settings, sweep: three sweeps, one setting changed at a time
experiments/report.py    14.04   norm_ratio, outcomes, changes: the reproduction report, from the logs
experiments/recorded/grokking/   14.03's long run (3 seeds, 5000 steps); recorded/ablations/ 14.04's runs
```

An experiment never imports another (06.02's convention), so the claims
live in predictions.py, which claims.py prints and report.py judges, and
the loop lives in arithmetic.py, which grokking.py and ablations.py share.
models/gpt.py is not changed: every run builds GPT(V, 4, layers=2,
heads=4, width=128) (vocabulary p + 4, context 4: the model reads a, op,
b, = and is scored on its guess at c at the last of them).

### What was read, at the source

- Power, Burda, Edwards, Babuschkin and Misra (2022), "Grokking:
  Generalization Beyond Overfitting on Small Algorithmic Datasets", arXiv
  2201.02177v1 (the only version), the PDF from arxiv.org, read whole (10
  pages: sections 1 to 4, appendix A.1 to A.5). Figures 1, 2 and 4 looked
  at closely (rendered at 300 to 600 dpi); 3, 5, 6 and 7 looked at, not used.
  The set-up, quoted (each is in predictions.SETUP with its place):
  appendix A.1.1, "(for a prime number p = 97)", x/y "for 0 <= x < p,
  0 < y < p", "equations of the form <x><op><y><=><x o y>", "For each
  training run, we chose a fraction of all available equations at random
  and declared them to be the training set, with the rest of equations
  being the validation set."; A.1.2, "a standard decoder-only transformer
  ... with causal attention masking, and calculated loss and accuracy only
  on the answer part of the equation", "a transformer with 2 layers, width
  128, and 4 attention heads, with a total of about 4 x 10^5 non-embedding
  parameters", "AdamW optimizer with learning rate 10^-3, weight decay 1,
  beta1 = 0.9, beta2 = 0.98, linear learning rate warmup over the first 10
  updates, minibatch size 512 or half of training dataset size (whichever
  was smaller) and optimization budget of 10^5 gradient updates", "we
  chose not to anneal the learning rate"; for section 3.1.1 "5 x 10^5
  optimization steps"; for section 3.1 (figure 1) "we increased the
  optimization budget to 10^6, and used Adam optimizer with no weight
  decay"; "3 random seeds, with the exception of experiments in section
  3.1.1, where we've aggregated results over 7 random seeds". (The paper's
  symbols are written in ASCII here: the circle as o, beta as beta, the
  angle brackets as < >.)
  The claims, quoted, are in predictions.CLAIMS with their places. Read off
  the figures (by eye, so good to a factor of about 2 on a log axis):
  figure 1 left, the training curve passes 99% at about 700 steps, the
  validation curve leaves chance at about 3 x 10^4 to 5 x 10^4 and reaches
  99% at about 5 x 10^5 to 10^6 (lighter curves, other seeds, later);
  figure 1 center (S5, median steps to 99% validation): about 1.1e5 at 30%
  of the data, 2.5e4 at 40%, 1.4e4 at 50%, 1.5e4 at 60%, 6.5e3 at 70%,
  2.7e3 at 80%; figure 2 right (best validation accuracy in 10^5 steps,
  weight decay 1, mean of 3 seeds): x/y about 0.35 at 20% of the data and
  1.0 from 25%, x - y from 25%, x + y from about 20%; figure 2 left (S5):
  AdamW with weight decay 1 generalises from about 35 to 40% of the data,
  minibatch Adam without it only from about 85%; figure 4, the validation
  loss of figure 1's run rises from about 2.3 (its chance line) at 10^2 to
  a peak of about 20 near 8 x 10^4 and is back near 0 at 10^6.
- The authors' code, github.com/openai/grok (MIT), at commit 3d64b1d8c1d5
  (2024-03-16, the default branch main): README.md, scripts/train.py,
  grok/data.py and grok/transformer.py whole; grok/training.py's
  arguments, data loaders, scheduler, optimizer (CustomAdamW), _accuracy,
  _step and train. Not read: measure.py, metrics.py, visualization.py, the
  notebook, the other scripts. What the code does that the text does not
  say:
  - Each equation is "<|eos|> a op b = c <|eos|>" (7 tokens; the model
    reads the first 6), and the loss and accuracy are over every token
    after "=": c and the end token. The end token is always the same, so
    the loss of a guess is (ln 97 + 0) / 2 = 2.29: that is figure 4's
    "Chance level loss" line at about 2.3, which is not ln 97 = 4.57. An
    equation counts as right only when both tokens are. We score c alone,
    as the text says ("only on the answer part of the equation"): a guess
    is 4.575 nats here. Figure 4's peak of about 20 is so about 9 times
    its chance line; predictions.CLAIMS compares like with like.
  - Division is built as a = b x c for c in 0..96, b in 1..96: the same
    9312 equations as x/y for 0 < y.
  - The split: the equations are shuffled once with
    np.random.RandomState(seed=0) and the first train_pct % taken, so every
    run of a given fraction has the same split; only the starting weights
    and the batches change with the seed. The text says each run chose its
    fraction at random; data/modular.py follows the text (a split for each
    seed). Not measured whether it matters.
  - The model (transformer.py): post-norm blocks (LayerNorm(x +
    attention(x)), then LayerNorm(a + MLP(a))), no last norm; ReLU; no
    bias in any Linear layer (the layer norms have theirs); fixed
    sinusoidal positions; an output Linear layer of its own (not tied);
    every layer left at PyTorch's own start (nn.Embedding N(0, 1),
    nn.Linear uniform within 1/sqrt(inputs)); the vocabulary is 239 tokens
    (2 special, 20 operator symbols, 97 residues, 120 permutations).
  - CustomAdamW over self.parameters(): weight decay on every weight,
    biases and layer norms too, as p <- p (1 - lr wd), PyTorch's AdamW
    form; ours is torch.optim.AdamW on every weight, the same.
  - The warmup: lr = step / 10 x max_lr for step <= 10 (so the first
    update is at rate 0) and max_lr after; ours (03.05's warmup_cosine with
    floor 1) is (step + 1) / 10 for the first 10 updates. A one-step
    difference, not measured.
  - Batches: min(512, ceil(n / 2)), a new random order each pass, the last
    batch of a pass smaller (n mod 512 equations); ours the same
    (data.batches). The validation set is scored whole after every pass.
  - Its argparse default weight_decay is 0; the paper's runs set 1.
- Nanda, Chan, Lieberum, Smith and Steinhardt (2023), "Progress measures
  for grokking via mechanistic interpretability", arXiv 2301.05217v3 (ICLR
  2023), read: section 3 (the set-up: one layer, d = 128, 4 heads, ReLU,
  learned positions, no LayerNorm, untied, P = 113, 30% of the pairs, full
  batch, AdamW at 0.001, weight decay 1, 40,000 epochs; "After around
  10,000 epochs, the network generalizes"), 5.1 to 5.3, appendix C.2.2 and
  D.1, figures 2, 7, 20, 26 and 27. Not read: section 4 (the mechanism)
  beyond its summary, the other appendices. Figure 7 (bottom right): the
  sum of squared weights peaks at about 3600 near epoch 1,000 and falls to
  about 2000 by 10k and about 1000 by 14k (the norm, its square root, from
  60 to 32: 0.53 of its peak). Appendix D.1 contradicts itself, and its
  figure: the sentence says "Smaller amounts of weight decay lead to
  slower grokking, while larger amounts of weight decay lead to faster
  grokking", then "it takes around 3k epochs for models to grok with weight
  decay lambda = 0.3, 5-10k epochs ... with lambda = 1.0, and 20k epochs ...
  with lambda = 3.0" (the numbers say the opposite); figure 27 shows weight
  decay 0.3 grokking at about 15 to 25k epochs and 3.0 at about 3 to 4k,
  agreeing with the sentence. predictions.CLAIMS takes the sentence and the
  figure. Section C.2.2: with P = 53, "With the original weight decay
  setting of lambda = 1, we found that the models never generalized.
  However, increasing the weight decay to lambda = 5 does allow the model to
  grok." (A smaller prime is not a faster problem; spike 8 below agrees.)
  Figure 26: no weight decay, no grokking in 40,000 epochs.
- Liu, Michaud and Tegmark (2023), "Omnigrok: Grokking Beyond Algorithmic
  Data", arXiv 2210.01117: the abstract only, read for the start finding
  below (it explains grokking by "the mismatch between training and test
  losses" against the weights' norm, and says "we are able to eliminate
  grokking for algorithmic datasets"). Its body was not read: a page may
  cite the abstract's words, nothing more.
- Not read: Keshav's "How to Read a Paper" and Schulman's guide (the
  outline lists them for the pages; nothing in the code uses them).

### Our model against the paper's

models/gpt.py's GPT at the paper's depth, width and heads (2 blocks, width
128, 4 heads, MLP 512): 410,240 weights, 396,800 of them outside the
embeddings and positions (the paper: "about 4 x 10^5 non-embedding
parameters"; theirs, counted from transformer.py, has no biases and an
untied output). Every way it differs from the paper's code (report.py's
MODEL prints them; none of them is in the paper's text, which says only
"a standard decoder-only transformer ... with causal attention masking"):
pre-norm blocks and a last layer norm (theirs post-norm, none); GELU
(theirs ReLU); learned positions (theirs fixed sinusoids); output tied to
the embedding (theirs a Linear layer of its own); biases in every Linear
layer (theirs none); GPT-2's start, sd 0.02 (theirs PyTorch's own, the
embedding sd 1); a vocabulary of p + 4 tokens (theirs 239); the model reads
4 tokens and is scored on c alone (theirs reads 6, scored on c and an end
token). Which of these decides the result was measured (spike 8, part 2):
the start. With GPT-2's small start the model generalises as fast as it
memorises at the paper's 50%; with a start 3 or 10 times larger, or
PyTorch's, it memorises and stays at chance, as the paper's figure 1. The
paper's whole model rebuilt in scratch code does the same with PyTorch's
start and fails to memorise with GPT-2's. Norm placement, activation,
positions and the tie were not each measured alone.

### 14.01 Reading a paper for what it claims

data/modular.py: tokens 0 to p - 1 are the residues, p is "=", p + 1, + 2,
+ 3 are "+", "-", "/" (SYMBOLS); equations(97, "/") has 9312 rows (b from
1), "+" and "-" 9409. divide uses Fermat's little theorem, pow(b, p - 2,
p); 20 / 15 = 66 mod 97 (66 x 15 = 990 = 10 x 97 + 20) is the example
claims.py prints. split shuffles with numpy's default_rng(seed) and takes
round(fraction x n): 4656 at 50%, 3259 at 35% (6053 to validate).
experiments/claims.py prints SETUP (12 settings, each with its quote and
place), the ten claims of predictions.CLAIMS (8 from the paper, 2 from
Nanda et al.), each with its place, its words, the paper's setting, what we
measure, the paper's number and the rule; then the baselines at the
paper's 50%: a guess 1/97 = 0.0103, loss ln 97 = 4.575 nats; the memoriser
(the training table, else the commonest training answer) training 1,
validation `0.007016 +- 0.001295` (3 splits; at 35% `0.007875 +-
0.001009`): below a guess, because the commonest answer of the training
set is the one most used up there, so the rarest in the rest. 0.2 s.
The rules, fixed before any run (predictions.py): "about" is within a
factor of 3 (a number read off a log axis); "below" and "above" are the
direction; a lower bound ("more than 6000 steps") settles "above" and can
rule out "below" and "about", nothing else.

### 14.02 The experiment from the text: modular arithmetic

experiments/grokking.py with arithmetic.py's train: x/y mod 97, AdamW at
0.001, betas 0.9 and 0.98, weight decay 1 on every weight, warmup over 10
updates then constant, batches of 512 (or half the training set), the loss
and accuracy of the guess at c only; accuracy and loss on the whole
training and validation sets at log_steps (0, then per_decade a factor of
ten, and the last). The default: 35% of the equations (3259 to train on,
6053 to validate), 350 steps, 3 seeds, 5 measurements a decade.
After 350 steps: training accuracy `0.964 +- 0.04124` (0.9165 to 0.9911),
validation accuracy `0.02027 +- 0.00539` (0.014 to 0.023: a guess 0.0103),
training loss `0.7171 +- 0.2552` nats, validation loss `4.906 +- 0.576`
(above a guess's 4.575: it is rising). One seed (1) reached 99% on training
at step 350; part 3 (14.03's) prints "never" for the rest. 35 s and 32 s
at load 5.6 to 6.3 (another agent training); the same bytes twice. That is
the failure the module starts from: stopped here, a learner would report a
model that memorises and does not generalise.
Why 35% and not the paper's 50%: with our GPT at 50% (spike 8, part 1)
training and validation accuracy rise together (630/630 with or without
weight decay), so there is no failure to see; a learner can run
`fraction=0.5` (the same 35 s) and see validation climbing with training.
Why 350 steps and 5 measurements a decade: memorising takes 350 to 450
steps on this set-up, and 3 seeds of 400 steps with 10 a decade took 49 s
at load 7: too close to the minute.
The paper's set-up is quoted in grokking.py's CONFIG comment and printed by
claims.py; what differs from it in every run: the fraction (35%), the steps
(350 here, 5000 in 14.03, at most 6000 in 14.04, against 10^5, and figure
1's 10^6 with Adam without weight decay), the model (above), the split (a
new one each seed, as the text says, not the code's one fixed split), the
loss on c alone (the text; the code adds the end token), and the warmup's
first step (ours at a tenth of the rate, the code's at 0). Training
accuracy is measured on the whole training set at each measured step (the
code averages the batches of a pass as it trains).

### Spike 8: where a laptop sees the late generalising

What a step costs: the paper's model reads 512 equations of 4 tokens a
step, about 5 GFLOP forward and backward; on this CPU 31 to 35 ms at load
4 to 7 (43 ms at load 13; 140 GFLOP/s, the same with 1, 4 or 10 threads),
and scoring both splits whole (9312 equations) 120 to 155 ms. So 10^5
steps is about an hour for one seed, figure 1's 10^6 about ten hours: the
paper's budget does not fit, and an hour of CPU holds about 100,000 steps
for everything. Explored on the Apple GPU (mps, 7 to 8 ms a step, at every
batch size from 64 to 512) to save the CPU, then confirmed on it. In the
list, "a/b" is the first measured step at which training / validation
accuracy was 99% or more, "never" not within the run, x/y mod 97, AdamW at
0.001 with betas 0.9 and 0.98, warmup 10, batches of 512 unless said, one
seed unless said; "ours" is models/gpt.py's GPT as it starts (GPT-2's
start, every weight with sd 0.02).

1. The paper's own fraction, 50%, with ours: no grokking at all. Weight
   decay 1: 630/630 (CPU, seed 0); without weight decay (figure 1's Adam)
   630/630, 501/501, 630/794 (seeds 0 to 2): it generalises as it
   memorises, and needs no weight decay to.
2. What decides it: the start. At 50% without weight decay (figure 1's
   optimiser), 5000 to 10000 steps:
   - ours with every weight 3 times larger (sd 0.06): 316/never, validation
     0.025 at 5000, its loss up to 10.5 (2.3 times a guess's);
   - 10 times larger: 630/never, 0.012, loss up to 16.6;
   - every layer back to PyTorch's own start (reset_parameters; with our
     tied output the scores start huge, a first loss of 112): 1995/never
     at 10000 (CPU), 0.016;
   - the paper's model as its code builds it (scratch code, not in the
     project: post-norm, ReLU, untied output, sinusoidal positions,
     PyTorch's start): 501/never at 10000, validation 0.017, its loss up to
     16.3 at 6309: figure 1's first 10^4 steps as the paper draws them;
   - the paper's model with GPT-2's start: it does not even memorise
     cleanly (training 0.97, validation 0.06 at 5000).
   So with a small start the model generalises at once; with a large one
   it memorises, and its validation loss climbs, as in figures 1 and 4.
   With weight decay 1 at 50%: the paper's model 1258/5011; ours 10 times
   larger 501/3981, 630/3162, 794/3162 (seeds 0 to 2): grokking at the
   paper's fraction, 4 to 8 times later; ours 3 times larger 398/1000,
   398/630, 501/794 (validation already 0.19 to 0.70 when training reached
   99%: no clean delay); ours with PyTorch's start (CPU) 2511/5000,
   validation 0.25 at the first; with PyTorch's start and an untied output
   1000/2511.
3. Less data, with ours and weight decay 1 (the paper's own pointer: the
   late generalising is "typical ... for dataset sizes that were close to
   the minimal dataset size for which the network generalized within the
   allotted optimization budget", section 3.1):
   - 40%: 501/1258 (2.5 times later);
   - 35%: 398/2511, 398/1995, 501/2511 (seeds 0 to 2; 5 to 6.3 times
     later; validation 0.016 to 0.029 at the first): chosen;
   - 33%: all three seeds stuck near a guess for thousands of steps
     (training 0.18 to 0.21, validation 0.15 at 12000; CPU agrees for
     seed 0). 33% of 9312 is 3073 = 6 x 512 + 1: every pass ends with a
     batch of one equation, and Adam takes a full-sized step on it. At
     33.2% (3092, a last batch of 20) seed 0 trains (1584/1584). The
     authors' iterator has the same smaller last batch, so their code
     would meet this too at such a fraction; a lesson on reproduction can
     use it as a detail no paper reports.
   - 30%: 316/never in 15000 (CPU, seed 0: validation 0.057, creeping up,
     a slingshot at 1258 where training accuracy fell to 0.72), 316/3981,
     398/6000 (seeds 1 and 2): longer and less certain;
   - 25%: 251/never in 5000.
   With ours 3 times larger at 35%: 199/2511, 199/1995, 199/2511 (10 to
   12.6 times later: a larger start memorises sooner, generalises no
   sooner); 10 times larger 398/5000 (seed 1).
4. Weight decay, with ours: at 40%, none 398/never in 8000 (validation
   0.03, its loss up to 11.85), 0.3 398/5011, 1 501/1258, 3 never memorises
   first (training and validation rise together, 0.80 and 0.76 at 8000,
   unsteady); at 35%, none 316/never in 8000 (loss up to 12.7), 0.3
   316/6309 and 316/3981, 3 5011/5011 (no memorising first).
5. A smaller prime is slower, not faster (as Nanda et al. found for 53): at
   50% with weight decay 1, p = 23 79/never in 5000 (validation 0.17), 31
   125/never (0.18; with weight decay 3 0.15; without, 0.045), 47 316/1258
   (training accuracy unsteady, 0.915 at the end), 47 at 40% 100/never
   (0.21). No problem small enough to grok inside a minute was found, so
   14.04's default reads its recorded runs.

The choice: the paper's set-up as its text gives it (x/y mod 97, AdamW,
weight decay 1, the rate, betas, warmup and batch), our GPT as built, and
one change, 35% of the equations instead of figure 1's 50%: the smallest
change that shows memorising first and generalising later on every seed
inside the hour. Not figure 1's Adam without weight decay: at 35% and 40%
that never generalises within 8000 steps, where the paper's needed close to
10^6. The start, the difference that decides it, is 14.04's third
ablation, at the paper's 50%.

### 14.03 The figure: memorise first, generalise much later

The long run, recorded in experiments/recorded/grokking/ (seed0 to seed2:
config.json, log.jsonl, summary.json; accuracy.svg and loss.svg, log step
axes, training dashed red and validation green as the paper's figure 1
colours them, loss.svg with a guess's ln 97 as a grey line; norm.svg;
output.txt, what it printed):

    python3 -m experiments.grokking steps=5000 per_decade=20 out=experiments/recorded

x/y mod 97, 35% of the equations, the paper's AdamW set-up, 3 seeds of 5000
steps, measured at 64 steps (20 a decade, so a "first step at 99%" is known
to within 12%). 428 s by its own clock (21:52:05 to 21:59:14), load 4.6 to
7.3 (another agent training), about 30 ms a step with the measuring.
Measured (seed 0, 1, 2):
- training accuracy first at 99%: step 398, 354, 446 (`399 +- 46`);
- validation accuracy then: 0.0162, 0.0240, 0.0289 (a guess: 0.0103);
- validation accuracy first at 99%: step 2238, 1778, 2511 (`2.18e+03 +-
  370`); its first step at 10% or more: 1584, 1000, 1584;
- how many times later: 5.6, 5.0, 5.6 (`5.43 +- 0.349`): about 0.7 of a
  decade on the log axis, where the paper's figure 1 has three;
- the validation loss rises while the training loss falls: from 4.64 to
  4.66 at the start (a guess: 4.575) to its peak, 5.83, 5.02 and 5.31 nats
  (1.27, 1.10 and 1.16 times a guess's, `1.18 +- 0.0897`) at steps 562, 501
  and 794, after training accuracy passed 99%; then it falls, to 0.080,
  0.042 and 0.034 at the end. The paper's figure 4: about 9 times its
  chance line (but figure 1's run had no weight decay; see 14.04, part 1,
  where ours without it reaches about 2.5 times a guess's and keeps
  climbing);
- the weights' norm: 27.4 at the start (GPT-2's start); its highest 27.6
  (step 1584), 27.5 (step 0), 28.6 (step 1995); when validation reached
  99%, 25.5, 23.0, 27.2 (0.93, 0.84 and 0.95 of the highest before then);
  at the end 26.2, 23.7, 23.6. It barely moves: weight decay 1 at rate
  0.001 takes a thousandth off each step, and the gradient puts it back.
  Nanda et al.'s figure 7 (a larger start, full batch) halves the norm
  (0.53) between memorising and generalising;
- at the end both accuracies 1.000 on every seed; the losses 0.048
  (training) and 0.052 (validation) nats.
Brief spikes: every seed has a step or two where training accuracy drops
for a moment (seed 0 at 1122 to 0.910, at 1584 to 0.959 and at 3981 to
0.925; seed 1 at 2238 to 0.895; seed 2 at 1000 to 0.928 and 1584 to
0.959), each back within a measurement or two. Nanda et al. (appendix
C.2.2) say two-layer models' grokking "is complicated by the slingshot
mechanism (Thilak et al., 2022)" (not read; whether these dips are it is
not measured).
The figure's shape is the paper's: training near 100% by step 400 while
validation sits at chance, then validation climbing from about step 1000
to 99% by 1800 to 2500. "Much later" is 5 to 6 times later here, not the
paper's thousand.

### 14.04 Ablations, and the report

experiments/ablations.py: three sweeps, one setting changed at a time from
14.03's run, each setting 3 seeds; a run stops at the first measured step
(10 a decade) at which validation accuracy is 99% (stop=True in
arithmetic.train), else at 6000 steps. A setting two sweeps share is run
once (settings()). Recorded in experiments/recorded/ablations/ (a folder
per setting, fraction<f>-decay<wd>-start<s>, seed0 to seed2 in each;
output.txt, what it printed):

    python3 -m experiments.ablations train=True out=experiments/recorded

1634 s by its own clock (21:59:14 to 22:26:29, load 5.7 to 10.3; 18 runs).
With 14.03's 428 s the module's recorded runs took 2062 s, 34 min 24 s of
wall clock, inside the hour. "a/b" is training / validation 99%:
1. Weight decay, 40% of the equations: none: 398/never, 398/never,
   398/never (best validation accuracy 0.027, 0.071, 0.077 in 6000 steps;
   the validation loss up to 2.6, 2.48 and 2.22 times a guess's, at steps
   5011, 3162 and 1995; the norm from 27.4 up to about 45); 0.3: 398/3981,
   398/3981, 398/2511 (median 3981; the norm up to 33, then down to 24 to
   27); 1: 501/1258, 501/1000, 501/1000 (median 1000).
2. The fraction, weight decay 1: 35% 398/2511, 398/1995, 501/2511 (median
   2511; the same runs as 14.03's, measured at 10 a decade instead of 20);
   40% median 1000 (above); 50% 630/630, 630/794, and seed 2 never: it
   neither memorised nor generalised, stuck from step 600 on near training
   0.67 and validation 0.34 (0.80 and 0.27 at 6000): at the paper's own
   fraction one seed of three found neither solution in 6000 steps. Median
   794. So k (steps ~ 1 / fraction^k, 35% to 50%) = ln(2511 / 794) /
   ln(0.5 / 0.35) = 3.23, where figure 1 (center) gives about 4 on S5 from
   30% to 50%; and training 99% comes sooner with less data (398 at 35%
   against 630 at 50%), as section 3.1.1 says.
3. The start, 50% of the equations, weight decay 1: GPT's own (GPT-2's,
   sd 0.02): 630/630, 630/794, never/never (1.0 and 1.3 times later: no
   grokking); every weight but the layer norms' 10 times larger
   (scaled_start): 501/3981, 630/3981, 794/3162 (7.9, 6.3 and 4.0 times
   later; validation accuracy 0.012 when training reached 99%), the norm
   from 109 down to 23.5, 27.2 and 33.6 when validation reached 99% (0.21
   to 0.31 of its start: the fall Nanda et al.'s figure 7 shows, which
   GPT-2's small start does not need). At the paper's fraction and with
   the paper's text's optimiser, a large start is what brings back the
   late generalising. (Spike 8 has the same without weight decay: GPT's
   own start generalises at once, 3 or 10 times larger never in 5000.)
The default (train=False) trains nothing: a minute of CPU holds about 1500
steps of this model (30 ms a step, measured above), and no setting of the
table generalises in that (the fastest, 50% with GPT's own start, needs
about 630 steps for one seed, 1900 for three; spike 8 found no smaller
problem that groks sooner). It reads the recorded runs and prints their
table, in 1.0 s; the page should say so, and give train=True's time (about
27 minutes at load 6 to 10).

experiments/report.py reads the two recorded folders (settings figure= and
ablations=), computes each claim's number (outcomes), judges it by its
rule (predictions.verdict), lists what differs from the paper's set-up
(changes, against predictions.SETUP) and how the model differs (MODEL,
words only), and what the start did; it prints the report and writes it to
<out>/report/report.txt. 0.9 s. Every number in it comes from a log or a
config.json; the paper's numbers and the rules come from predictions.py.
The report on the recorded runs (ours: the median of 3 seeds):

    claim         the paper                    ours                                 verdict
    memorise      under 1000 steps             398 (398, 354, 446)                  held
    near_chance   about 0.01                   0.024 (0.0162, 0.024, 0.0289)        held (below 0.05)
    late          about 1000 times later       5.62 (5.62, 5.02, 5.63)              did not hold
    generalise    about 0.99                   1.0 (every seed)                     held
    loss_rises    about 9 times its chance     1.16 (1.27, 1.10, 1.16)              held (above 1)
    less_data     k about 4 (S5)               3.23 (35%: 2511, 50%: 794)           held (above 1)
    train_sooner  below 1                      0.632 (35%: 398, 50%: 630)           held
    decay         about 0 without (S5, 50%)    0.0583 at 40% (0.027, 0.071, 0.077)  held (below 0.5)
    more_decay    about 2 to 4 (Nanda)         3.98 (0.3: 3981, 1: 1000)            held (above 1)
    norm_falls    about 0.53 (Nanda)           0.926 (0.926, 0.839, 0.95)           held (below 1)

9 held, 1 did not hold. What a page may say about each:
- memorise, near_chance, generalise: held as the paper states them, at
  35% of the equations and the text's AdamW (not figure 1's 50% and Adam).
- late: did not hold. Figure 1's thousand-fold delay is figure 1's set-up:
  Adam without weight decay for 10^6 steps, and the paper's large start.
  With the text's weight decay 1 ours is 5 to 6 times later; without
  weight decay (14.04, part 1) it never generalises within 6000 steps, so
  the paper's 10^6 cannot be checked in an hour (it would be about ten
  hours a seed on this CPU).
- loss_rises: held in direction only; 1.1 to 1.3 times a guess's, where
  figure 4 shows about 9 times its chance line. Without weight decay ours
  climbs to 2.2 to 2.6 times and is still climbing at 6000 (part 1), the
  shape of figure 4's first 10^4 steps.
- less_data: held; k = 3.23 on x/y between 35% and 50%, figure 1's S5
  about 4 between 30% and 50%: the same steepness, on another operation
  and range. Below 35% our runs are erratic (spike 8: 33% stuck, 30% one
  seed in three not by 15000).
- train_sooner: held.
- decay: held: without weight decay no seed generalises at 40% in 6000
  steps; with it every seed does by 1258. At 50% with GPT's own start (spike
  8, part 1) weight decay makes no difference: the model generalises at
  once either way.
- more_decay: held, and close to Nanda et al.'s numbers (0.3 about 4
  times slower than 1 here; their figure 27 about 2 to 4).
- norm_falls: held in direction only (0.93 of the highest), far from
  Nanda et al.'s 0.53 for GPT's own small start; with the start 10 times
  larger (part 3) the norm falls to 0.21 to 0.31 of where it began.

### Tests (module 14)

`./learn test research 14`: all 4 pass, 1 min 58 s at load 6 to 7 (14.01
1.2 s, 14.02 43.9 s, 14.03 62.9 s, 14.04 9.8 s). Each runs its exact checks
first (inside()), then its experiment:
- 14.01: every pair once for +, - and / at p = 5, 7 and 97 (b from 1 for
  division), every c right (c x b = a mod p for division), the tokens a, op,
  b, =, c; split disjoint, covering, round(fraction x n), seeded; divide's
  ZeroDivisionError; the claims' fields and rules; verdict on every rule
  and a lower bound; the memoriser right on every training equation and
  near chance (its validation accuracy is the commonest training answer's
  share); then claims.py's output (chance 0.0103, the memoriser under 0.03).
- 14.02: log_steps; score against a direct sum of -ln p(c); train with
  torch.optim.AdamW and data.batches watched (betas, the weight decay on
  every weight in one group, the rate 1/10, ..., 1 over 10 updates then
  constant, batches of half of 44 equations), the log at log_steps, a tiny
  table learned; then the default: every seed's training accuracy over 0.9
  and validation under 0.05, the log from 0 to 350 with both splits, the
  validation loss 2 nats or more above the training loss, the curves; a
  tiny run twice, the same bytes.
- 14.03: weight_norm against the norm of every weight laid end to end;
  first_step and milestones on a log written by hand; the recorded run
  (every seed's config the same but the seed, the log from 0 to 5000 with
  the norm, the three curves, output.txt; every seed memorised under 1000
  steps with validation under 0.05 then, validation 99% three or more times
  later, its loss above ln 97 between the two, the norm lower at the second
  than at its highest); then a run at 50% of 800 steps, 2 seeds (both
  accuracies reach 99%, the norm lower than at the start), and a tiny run
  twice. LEARN_RERUN_LONG=1 runs the long run again from its config (about
  7 minutes).
- 14.04: settings and its sharing; median_steps; scaled_start (the layer
  norms untouched); read_seeds, read_runs, sweep, norm_ratio and outcomes on
  a fixture of runs written with lab.Run whose answers are known; changes;
  the recorded ablations (every setting, 3 seeds, each stopped at its 99%
  or at 6000; without weight decay no seed generalises, with 1 every one;
  the median steps fall as the fraction grows; 10 times the start more than
  twice as late); the default's table (every median as the summaries give
  it); the report (printed as written, memorise equal to the summaries'
  median, a verdict for each of the 10 claims, the fraction named as
  changed); a tiny train=True sweep twice, the same bytes, and the report on
  it. The ablations are not rerun by any test (half an hour).
`./learn check-skeleton research 14` ok, 4.6 s (14.01 fails at equations,
14.02 at log_steps, 14.03 at weight_norm, 14.04 at settings).
With module 14, the whole track (modules 00 to 08 and 14; another agent
training, load 6 to 10): `./learn test research` 44 tests, all pass, 14 min
17 s (14.02 57.9 s, 14.03 80.2 s there); `./learn check-skeleton research`
ok, 48 s; `./learn check-timeline research` ok, 3 min 17 s, the project
has 174 files at 14.01, 176 at 14.02, 189 at 14.03 (13 of them the
recorded figure) and 246 at 14.04 (55 the recorded ablations); `./learn
selftest` ok (269 tests); `./learn check` reports exactly four problems,
`research/14.0N: test has no lesson doc`, until the pages are written.

### For the harness, and what a page writer meets

- No harness change. track.py's module-14 part (last in the file) adds
  the four experiments to EXPERIMENTS, places experiments/grokking.py at
  14.02 by FILES_FROM (all its code is in arithmetic.py's regions and
  @from blocks: no region of its own), and puts
  "experiments/recorded/grokking/*" (14.03) and
  "experiments/recorded/ablations/*" (14.04) before 06.04's wider glob, as
  modules 07 and 08 do, with DATA lines for both.
- The timeline at 14.02 shows arithmetic.py with train's 14.02 form (no
  norm in the log, no stop, measure without its return) and grokking.py
  without part 3; 14.03 adds weight_norm, first_step, milestones and part
  3; 14.04 the stop and the readers. checked with ./learn files research
  --at 14.02.
- Nothing in the module downloads anything: a session block from 14.02 on
  says needs="torch"; 14.01 is numpy only.
- 14.04's default trains nothing: it reads experiments/recorded/ablations,
  which the project has from 14.04 (FILES_FROM), so verify replays it in
  a second or two. train=True makes the runs again (about half an hour).
- 14.01's lesson has 06.02's convention to explain: predictions.py (no
  main) holds what claims.py prints and report.py judges, because an
  experiment never imports another.

### Checked, and not checked

Checked at the source: every quote of the paper in predictions.py and here
(the PDF's text, extracted with pdftotext and read against the page
images); the figures' readings (by eye at 300 to 600 dpi: a factor of
about 2 on their log axes); the authors' code at the commit named; Nanda
et al.'s set-up, figures 7, 26 and 27 and the D.1 contradiction; the
Omnigrok abstract. Not checked: why figure 1's validation curve leaves
chance near 5 x 10^4 (no explanation in the paper); whether the code's
fixed split or its end-token loss changes our results (not run); norm
placement, activation, positions, the tie and the biases one at a time
(only the start was isolated, and the paper's whole model rebuilt in
scratch code); learning rates other than 10^-3 (the paper: a window of
"within 1 order of magnitude"); other operations than x/y (figure 2,
right: x - y "about the same amount of data", not run); S5 (the paper's
figure 1 center and figure 2 left are on S5; ours on x/y, which the claims
table says beside each). Thilak et al.'s slingshot paper and the Omnigrok
body were not read. Nothing was run on Linux.

### The lessons (written 2026-11-24, after the code)

Four lessons, the module page, 14 figures (art/research/figs14.py) and the
cover (art/outlines/research_art.py, from the recorded runs, its numbers
asserted). Read at the source for the pages, beyond what is above:
- S. Keshav, "How to Read a Paper", the PDF the outline links (3 pages),
  whole: the three passes (2.1 first pass, five to ten minutes, and its
  "five Cs"; 2.2 second, the figures, "Are the axes properly labeled? Are
  results shown with error bars"; 2.3 third, "attempt to virtually
  re-implement the paper: that is, making the same assumptions as the
  authors, re-create the work"). 14.01 cites only these.
- J. Schulman, "An Opinionated Guide to ML Research" (posted 2020/01/24),
  whole: "Personal Development" ("I recommend spending a lot of time
  reimplementing ideas from papers, and comparing your results to the
  published ones"; "where the desired level of performance is known") and
  "Keep a Notebook, and Review". Cited in 14.01 and 14.04's Go deeper.
- The grokking PDF again, whole, with figure 1 (page 1), figure 2 (page 3)
  and figure 4 (page 7) looked at: the readings above agree (figure 1's
  training passes 99% near 5 x 10^2 to 7 x 10^2, validation leaves chance
  near 5 x 10^4; figure 2 left, minibatch Adam near 0 at 50% and AdamW with
  weight decay 1 near 100 from about 40%; figure 4's chance line about 2.3
  and peak about 20 near 10^5). Figure 1's red training curve has brief
  dips after 10^3, as ours does. Section 3.1 states the delay in other
  words than the caption ("starts increasing beyond chance level only
  after 1000 times more optimization steps"), where the caption's own "very
  little evidence of any generalization until 10^5" is a hundred times;
  14.01 says so. Section 3.1's "For larger dataset sizes, the training and
  validation curves tend to track each other more closely" is 14.02's
  reason for 35%. Appendix A.3 on the second descent of the loss being
  perhaps not Nakkiran et al.'s double descent, cited in 14.03.
- openai/grok at 3d64b1d8c1d5 again: README.md (the command
  `./scripts/train.py`), scripts/train.py (parses training.add_args and
  trains), and training.py's argument defaults: math_operator "+",
  train_data_pct 5, weight_decay 0, max_lr 1e-3, warmup_steps 10, n_layers
  2, d_model 128, n_heads 4. So the README's command trains x + y on 5% of
  the equations without weight decay (14.01). data.py: make_data's shuffle
  with RandomState(seed=0) and its default seed (the one split),
  "<|eos|> ... <|eos|>" around every equation; ArithmeticIterator's
  min(512, ceil(n / 2)) and its smaller last batch. training.py's _step
  (loss on everything after "=") and _accuracy (an equation right only when
  every token after "=" is). transformer.py: no explicit initialisation
  anywhere (PyTorch's own start).
- Nanda et al. again: section 3 (no LayerNorm, untied), figure 7 looked at
  (page 8: the sum of squares peaks near 3650 at about epoch 1000 and is
  near 1000 from about 14k on: the norm to about 0.52 of its peak), section
  5.3 ("when networks are provided with enough data, there is no longer a
  gap between the train and test losses"), appendix D.1's sentence and
  figure 27 looked at (page 28: weight decay 0.3 groks at about 15k to 25k
  epochs over its seeds, 3.0 at about 2k to 4k; the caption "Less
  aggressive weight decay leads to slower grokking").
- Omnigrok (Liu, Michaud and Tegmark), the arXiv abstract page (v2, 23 Mar
  2023): the abstract only, as above. 14.04's Go deeper says so.

Measured for the pages (this machine, load 11 to 14, other agents
training; one run each unless said):
- The weights' norm at the start, 27.45, is mostly the layer norms: 5
  layer norms of 128 (two a block and the last), 640 gains at 1 and 640
  biases at 0, give sqrt(640) = 25.30; the other 408,960 numbers give
  10.64. Started 10 times larger (scaled_start leaves the layer norms),
  109.4. Nanda et al.'s model has no layer norm, so our norm_falls ratio
  (0.926) and their 0.53 do not measure the same thing; the logs do not
  hold the two parts apart. 14.03, How it works, shows it as a session.
- 14.02's Break it: batch=543 at 35% (3259 = 6 x 543 + 1, a last batch of
  one equation each pass): after 350 steps training accuracy `0.02557 +-
  0.0009374`, validation 0.01828, training loss 4.517 (3 seeds, 47 s): no
  memorising at all, against 0.964 with 512. The same with the paper's
  batch at fraction=0.33 (3073 = 6 x 512 + 1): training 0.02473 after 350
  steps (44 s); at fraction=0.332 (a last batch of 20): 0.1171 (47 s).
  fraction=0.5 at 350 steps: training 0.1861, validation 0.05019 (seed 0
  0.307 and 0.11, the others 0.15 and 0.10 with validation near chance):
  not decisive in 350 steps, so 14.02's figure draws 14.04's recorded 50%
  runs instead.
- 14.03's Break it: weight_decay=0.0, 350 steps: every seed training 1.000
  (99% by step 350), validation 0.01625, validation loss 6.111 (1.34 times
  a guess's, its highest at the last step), the norm 34.4, 34.4, 34.7 at
  the end (with weight decay 27.4, 27.2, 26.9). 52 s.
- 14.04's Break it: late's rule ("about", 1000) made ("above", 1.0): the
  report prints "held: 10, of 10 claims". Nothing else changes.
- The default runs as the pages show them: claims 1.2 s; grokking at 14.02
  42 s and at 14.03 37 s (load 13); ablations and report under a second.
  Every number on the pages is the same as above; the seconds vary.

"Held in direction only": the report's verdicts are 9 held and 1 did not
hold, by the rules of predictions.py. 14.04 and figs14.py's verdicts figure
read two of the nine as held in direction only: a direction rule (above or
below a line) that held where the paper's number is more than 3 times
further from the rule's line, on a log scale, than ours (the factor
"about" allows). That marks loss_rises (ln 9 = 2.20 against ln 1.16 =
0.15) and norm_falls (0.63 against 0.077), and no other (less_data 1.39
against 1.17, more_decay the middle of 2 to 4, 1.04, against 1.38,
near_chance 1.61 against 0.73; decay's "about 0" has no log). It is a
reading made after the runs, said so on the page, and changes no verdict.

## Module 13: experiments that hold up

Built by one agent on 2026-11-24 and 25, on the reference machine above
(Apple M4 Pro, Python 3.12.7, numpy 2.4.3, PyTorch 2.10.0, 10 threads by
default, scipy 1.17.1 installed and used by the tests only), shared all
the while with three other agents' work: load average 10 to 21, most of
it 14 to 19. Every time below says its load; times at a load under 6 were
not seen. Every lesson takes a result the track already reported and tries
to break it.

### The files

```
lab/stats.py             13.01   best_of: the expected best of n trials, worked out from N
                         13.02   sem, t_density, t_cdf, t_quantile, interval, difference (paired or Welch's),
                                 bootstrap, seeds_needed, batch_sem
                         13.03   normal_best: the expected largest of k normal draws
                         13.04   power_law, power_interval: a line through (ln x, ln y), and its prediction
lab/__init__.py          13.01-04 the new names re-exported, one @from line a lesson
experiments/baseline.py  13.01   draw_rates, run_one (regions); HYPOTHESIS, RULE, verdict, main
experiments/errorbars.py 13.02   position_bits (region); build, read, describe, main
experiments/fooled.py    13.03   hold_back, shrink, two_nearest, exact_copies, shared_grams (regions); raw,
                                 choose_by_test, twins, text, main
experiments/scaling.py   13.04   counted, predict (regions); table, plot, read, main
experiments/recorded/errorbars/  13.02's runs at 10 seeds a side (output.txt, pairs.svg)
experiments/recorded/scaling/    13.04's long run (output.txt, curves.svg, fit.svg, fit/seed0/summary.json)
tests/1301_... to 1304_...       one a lesson
```

Nothing earlier changes: models/gpt.py, experiments/language.py,
lab/safetensors.py and data/fetch.py are untouched (other agents were
changing them); lab/stats.py's earlier regions are as they were, and its
new imports and docstring lines carry @from markers. errorbars.py
reproduces 08.02's heads comparison to the last digit (seeds 0 to 2: `3.433
+- 0.01583` and `3.407 +- 0.009038`, t = -2.4): the same models, data and
draws.

### What was read, at the source

Each paper fetched from arXiv on 2026-11-25 (the PDF; its text extracted
with pdftotext and read section by section; every quote here was found in
that text again by search). The playbook's README.md from its
repository's main branch, whose latest commit was 7554a51f5d30
(2024-06-13).

- Henderson, Islam, Bachman, Pineau, Precup and Meger, "Deep Reinforcement
  Learning that Matters", arXiv 1709.06560v3 (AAAI 2018). Read: the
  sections on hyperparameters, random seeds and trials, and reporting
  evaluation metrics, the conclusion, figure 5. The experiment 13.02's
  part 6 mirrors: "We perform 10 experiment trials, for the same
  hyperparameter configuration, only varying the random seed across all 10
  trials. We then split the trials into two sets of 5 and average these two
  groupings together", figure 5: "TRPO on HalfCheetah-v1 ... The average
  2-sample t-test across entire training distribution resulted in t =
  -9.0916, p = 0.0016", and "We demonstrate that the variance between runs
  is enough to create statistically different distributions just from
  varying random seeds." On baselines (13.01): "poor hyperparameter
  selection can be detrimental to a fair comparison against baseline
  algorithms", and the conclusion: "it is important to find the working set
  which at least matches the original reported performance of baseline
  algorithms through standard hyperparameter searches". On reporting: they
  run five seeds; bootstrap intervals with "10k bootstrap iterations and
  the pivotal method"; the 2-sample t-test, Kolmogorov-Smirnov and
  bootstrapped percent differences; a bootstrap power analysis ("If there
  is a small percentage of significant values, a larger sample size is
  needed"); "While there can be no specific number of trials specified as a
  recommendation". Not found: a rule that the baseline gets the same
  search budget as the new method (13.01 takes that from the playbook).
- Bouthillier et al., "Accounting for Variance in Machine Learning
  Benchmarks", arXiv 2103.03098 (MLSys 2021). Read: sections 1 to 5 and
  appendix C. The sources of variance they vary: "i) the data sampling, ii)
  data augmentation procedures, iii) model initialization, iv) dropout,
  and v) data visit order in stochastic gradient descent", plus the
  hyperparameter search and numerical noise; "Bootstrapping data stands out
  as the most important source of variance. In contrast, model
  initialization generally is less than 50% of the variance of bootstrap,
  on par with the visit order of stochastic gradient descent"; the test set
  as a sample: "a simple binomial can be used to model the sampling noise
  in the measure of the prediction accuracy ... If errors are correlated,
  not i.i.d., the degrees of freedom are smaller and the distribution is
  wider"; "The three hyperparameter optimization methods induce on average
  as much variance as the commonly studied weights initialization"; their
  first recommendation, "As many sources of variation as possible should
  be randomized whenever possible"; the decision by P(A > B), "a threshold
  of 0.75"; "29 trainings" for 5% false negatives at that threshold
  (appendix C); pairing, "highly recommended to increase statistical
  power ... re-using the same seed for A and B in each pairs"; in their
  simulation "The single point comparison ... suffers from both high false
  positives (~10%) and high false negatives (~75%)". Not used: their
  out-of-bootstrap resampling of the data splits (our splits are fixed).
- Miller, "Adding Error Bars to Evals: A Statistical Approach to Language
  Model Evaluations", arXiv 2411.00640. Read: sections 1 to 5. The test
  set as a sample: "Suppose that the questions in an eval do not represent
  all possible questions, but instead were drawn at random from a
  (hypothetical, infinite, unseen) super-population of questions"; the
  standard error sqrt(Var(s) / n) and "sbar +/- 1.96 x SE"; clustered
  standard errors when questions come in groups ("clustered standard
  errors can be over 3X larger than naive standard errors"; 13.02's
  batch_sem is that idea with consecutive windows as the groups); paired
  differences, Var(A - B) with "- 2 Cov(s_A, s_B)", "paired differences
  represent a 'free' reduction in estimator variance", "We therefore
  recommend using the paired version of the standard error estimate
  wherever practicable"; the power analysis, n = (z_alpha/2 + z_beta)^2
  (omega^2 + ...) / delta^2 (seeds_needed is the same with t's for z's,
  since seeds are few); the variance of a score split into "the variance
  associated with choosing questions from the super-population, and the
  mean conditional variance" (resampling answers). Miller's paper treats
  questions and sampled answers, not training seeds: "Not found": any
  treatment of training-seed variance.
- Recht, Roelofs, Schmidt and Shankar, "Do ImageNet Classifiers Generalize
  to ImageNet?", arXiv 1902.10811v2 (ICML 2019). Read: abstract, sections 1
  to 3.3, 5.1, 5.2, appendix B.1 and B.2 (CIFAR-10), C.1.1 (near-duplicates
  for ImageNet). What they did: "We build new test sets for the CIFAR-10 and
  ImageNet datasets ... By closely following the original dataset creation
  processes" (2,000 images for CIFAR-10, 10,000 for ImageNet), and "find
  accuracy drops of 3% - 15% on CIFAR-10 and 11% - 14% on ImageNet". What
  they concluded: "Our results suggest that the accuracy drops are not
  caused by adaptivity, but by the models' inability to generalize to
  slightly 'harder' images than those found in the original test sets";
  the new accuracies are a line in the old (acc_new = 1.69 acc_orig -
  72.7% on CIFAR-10), "neither dataset sees diminishing returns"; with a
  caveat, "it could be that any test set adaptivity leads to a roughly
  constant drop in accuracy". Near-duplicates (appendix B.2.2): "we found
  about 800 images in the original CIFAR-10 test set that we would
  classify as near-duplicates (8% of the entire test set). Moreover, most
  classifiers have accuracy between 99% and 100% on these near-duplicates",
  and the arithmetic "acc = 0.92 acc_true + 0.08 acc_nd" giving at most
  0.6 points; found by "the top-10 nearest neighbors in both l2-distance
  and the SSIM (structural similarity) metric", a pair counted when "both
  images have the same object in the same pose", "different zoom, color
  scale, stretch ... or small shifts" included. Sampling error: "With
  10,000 data points ... a Clopper-Pearson 95% confidence interval for the
  test accuracy has size of at most +-1%".
- Kaplan et al., "Scaling Laws for Neural Language Models", arXiv
  2001.08361v1. Read: sections 1.1, 1.2, 1.3, 2 to 2.3, 3.1 to 3.2 (figures
  5 and 6), 4.1 and 4.2, 5.2 (equation 1.6 and table 3), appendix A, D.6 and
  D.7. The law (equation 1.1): "For models with a limited number of
  parameters, trained to convergence on sufficiently large datasets: L(N) =
  (N_c / N)^alpha_N; alpha_N ~ 0.076, N_c ~ 8.8 x 10^13 (non-embedding
  parameters)". L is "the cross entropy loss in nats", "averaged over a
  1024-token context", on WebText2's test text. What N counts (equation
  2.1): "N ~ 2 d_model n_layer (2 d_attn + d_ff) = 12 n_layer d_model^2 ...
  where we have excluded biases and other sub-leading terms. Our models
  also have n_vocab d_model parameters in an embedding matrix, and use
  n_ctx d_model parameters for positional embeddings, but we do not
  include these when discussing the 'model size' N; we will see that this
  produces significantly cleaner scaling laws"; figure 6: "When we exclude
  embedding parameters, the performance of models with different depths
  converge to a single trend. Only models with fewer than 2 layers or with
  extreme depth-to-width ratios deviate significantly from the trend". The
  conditions: "a fixed 2.5 x 10^5 steps with a batch size of 512 sequences
  of 1024 tokens", "a 3000 step linear warmup followed by a cosine decay
  to zero" (section 2.2); WebText2 has 2.29 x 10^10 tokens (section 2.3);
  "Here we have trained to near convergence on the full WebText2 dataset
  and observe no overfitting (except possibly for the very largest
  models)", over sizes from "(n_layer, d_model) = (2, 128)" to billions
  (section 3.2), "768 to 1.5 billion non-embedding parameters" in all.
  Appendix D.7: "For L(N) we also do not include very small models with
  only 1 layer in the fit, and we exclude the largest models that have not
  trained fully to convergence". Training for a fixed number of steps is
  equation 1.6, L(N, S) = (N_c / N)^alpha_N + (S_c / S_min(S))^alpha_S:
  at a fixed S a power law plus a constant. On precision: "The precise
  numerical values of N_c, C_c^min, and D_c depend on the vocabulary size
  and tokenization and hence do not have a fundamental meaning"; the loss
  from seed to seed "is roughly 0.02" (section 4.2); no standard error is
  given for alpha_N. Larger models are "more sample-efficient than small
  models, reaching the same level of performance with fewer optimization
  steps (Figure 2)". Their learning rate fell with size by a rule of thumb
  (D.1), LR(N) ~ 0.003239 - 0.0001395 log(N); not used here (one rate for
  every size; the paper does not say which logarithm).
- The Deep Learning Tuning Playbook (Godbole, Dahl, Gilmer, Shallue,
  Nado). Read: "Identifying scientific, nuisance, and fixed
  hyperparameters", "Creating a set of studies", "Striking a balance ...",
  "Why use quasi-random search ...", "How many trials are needed ...",
  "Detecting whether a change is useful with isolation plots", "Determining
  whether to adopt a training pipeline change". 13.01's rule: "Nuisance
  hyperparameters are those that need to be optimized over in order to
  fairly compare different values of the scientific hyperparameters"; the
  learning rate of each optimiser is a different hyperparameter ("the
  conditional hyperparameter called learning_rate is a different
  hyperparameter for optimizer="Nesterov_momentum" versus
  optimizer="Adam""); "For a fair comparison, the baseline should also have
  its learning rate equally well tuned"; "We would compare the two
  optimizers by selecting the best performing trial from each study"; on
  seeds, "before adopting a candidate change, consider running the best
  trial N times to characterize the run-to-run trial variance". It
  recommends quasi-random search ("jittered, shuffled grid search"); in
  "1-2 dimensions, grid search is also acceptable"; plain random search is
  "likely to be slightly less efficient". 13.01 draws plain random
  log-uniform rates, so that any n of them is a fair sample for best_of.
- PyTorch's documentation of torch.optim (2.10, "Constructing it"):
  `optimizer = optim.SGD(model.parameters(), lr=0.01, momentum=0.9)`, the
  hurried arm of 13.01.
- Not read: Schulman's "An Opinionated Guide to ML Research" (the outline
  lists it; nothing in the code uses it); Barz and Denzler's paper on
  CIFAR's duplicates (no comparison with its count is made); MNIST's own
  page (yann.lecun.com refused the connection on 2026-11-25; nothing about
  MNIST's writers or the order of its test file is claimed from it).

### 13.01 A hypothesis, and a baseline tuned as hard as your method

experiments/baseline.py: 03.03's network (784-256-256-10, relu, the
paper's 0..1 pixels), Adam against SGD with Nesterov momentum 0.9 (03.03's
pair), on the PyTorch-era loop (images.train_epoch and evaluate; loop.mlp
builds the network). Data: the first 10,000 training images to train on,
the last 10,000 of the 60,000 as validation (never trained on), the 10,000
test images only ever reported; 2 passes, batches of 128. Error in %.
1. HYPOTHESIS and RULE (module constants, printed first by every run):
   "Adam reaches a lower test error than SGD with Nesterov momentum 0.9 on
   this network after the same passes, when each optimiser's learning
   rate is found by the same search"; held if Adam is lower with Welch's t
   of 3 or more over the fresh seeds, the reverse if SGD is, a tie
   otherwise.
2. The search: draw_rates draws 8 numbers u in [0, 1) once (rng 0) and
   puts the same u's into each range, log-uniform: Adam 1e-4 to 1e-2, SGD
   3e-3 to 3e-1 (two decades each, about where 03.03's grids found each
   one's best). Every trial on seed 0; chosen on validation. Validation /
   test error of each trial, by rate: Adam 0.00011: 15.51/16.15, 0.00012:
   14.36/15.03, 0.00035: 9.36/10.15, 0.0016: 6.50/6.98, 0.0019: 5.96/6.50,
   0.0029: 5.54/6.08, 0.0042: 5.17/5.66, 0.0067: 5.59/6.56: chosen 0.00423;
   SGD 0.0032: 30.36/31.65, 0.0036: 28.93/29.96, 0.01: 12.42/13.57, 0.049:
   12.43/13.55, 0.056: 12.12/12.91, 0.086: 8.21/8.77, 0.13: 7.64/8.54,
   0.2: 8.04/8.92: chosen 0.127. Neither choice is at the edge of its range.
3. Fresh seeds 1 to 5, test error: Adam at 0.00423 `6.25 +- 0.488` (min
   5.77, max 6.94); SGD at the docs' 0.01 `14.6 +- 0.741`; SGD at its
   chosen 0.127 `7.06 +- 0.454`. The hurried comparison (Adam tuned, SGD at
   the docs' rate): SGD 8.37 points worse, t = +21.1, "held". The fair
   one: 0.81 points, t = +2.7, "a tie" by the rule written first (Adam
   lower on average, not by 3 standard errors). The winners' own trials
   (seed 0) on test: Adam 5.66 against 6.25 on fresh seeds, SGD 8.54
   against 7.06: one seed is not the setting's score, either way.
4. best_of over the 8 trials, n = 1 to 8, the expected best validation
   error and the test error of the one chosen: Adam 8.50 / 9.14, 6.21 /
   6.83, 5.57 / 6.17, 5.40 / 5.98, 5.32 / 5.87, 5.26 / 5.78, 5.22 / 5.71,
   5.17 / 5.66; SGD 15.02 / 15.98, 10.08 / 10.95, 8.67 / 9.51, 8.16 /
   9.00, 7.88 / 8.74, 7.75 / 8.63, 7.69 / 8.59, 7.64 / 8.54. A search of
   one trial (a rate picked at random in a sensible range) leaves SGD 6.5
   points behind on validation; of 8 trials, 2.5 (2.9 on test). Most of
   what 8 trials buy comes in the first 3 or 4 for both. best_of.svg draws
   it.
Tried before settling (all at load 14 to 15, the scaling run going):
trials=8 seeds=3 (the first default): the fair gap 0.81, t = +2.7 (Adam
6.53 +- 0.41, SGD 7.34 +- 0.325), 14 s. trials=16 seeds=5: the 8 extra
draws put SGD's choice at 0.222, near where it stops being stable: on
fresh seeds `8.84 +- 2.78` (one seed 13.5): the fair gap 2.27, t = +1.8. A
search on one seed rewards a rate that was lucky on that seed; the
playbook's "consider running the best trial N times" is the cure (not
built: the page can say it). trials=12 seeds=5 chose the same 0.222. The
default stays at 8 trials and 5 seeds.

### 13.02 Error bars: is the difference real?

experiments/errorbars.py: 08.02's part 3, 4 blocks of width 64 without
positions, 1 head of 64 against 4 heads of 16, windows of 32, 300 steps of
32, AdamW 0.003, the same seeds. The tools are lab/stats.py's (above) and
position_bits (window_bits' score position by position, so its spread can
be measured; its mean is window_bits to 1e-5).
1. Seeds 0 to 2 (the default): 1 head `3.433 +- 0.01583` (min 3.415, max
   3.444), 4 heads `3.407 +- 0.009038` (3.398 to 3.415), t = -2.4: 08.02's
   numbers to the last digit. One seed starts both arms from the same
   weights (torch.equal on every tensor: the heads change how q, k and v
   are cut, not their shapes) and the same batches (run.rng): 08.02's
   comparison was paired all along without saying so.
2. Each mean, its sem, and three intervals (95%): 1 head 3.4330, sem 0.0091:
   with Student's t at 2 degrees of freedom (4.30) 3.3937 to 3.4724; with
   the normal's 1.96 3.4151 to 3.4509; the bootstrap (10,000 resamples)
   3.4149 to 3.4442. 4 heads 3.4073, sem 0.0052: 3.3848 to 3.4297; 3.3970
   to 3.4175; 3.3975 to 3.4154. At 3 seeds the honest interval is 2.2 times
   the 1.96 one, and the bootstrap's is narrower still (3 numbers have 10
   distinct resamples: it knows only the spread they show).
3. The difference, 4 heads minus 1: -0.0258 bits per character. As two
   independent sets (Welch, its own degrees of freedom): -0.0582 to
   +0.0067, width 0.0649, not decided. As pairs (the interval of the three
   seeds' differences): -0.0441 to -0.0075, width 0.0366, decided: 4 heads
   lower. The runs of one seed move together: correlation +0.97 over the
   three seeds; the differences `-0.0258 +- 0.00736` (-0.0311 to -0.0174);
   4 heads lower on 3 of 3 seeds. Bootstrap of the pairs: -0.0311 to
   -0.0174 (too narrow again).
4. The test text as a sample. Seed 0's models scored position by position
   (55,754 positions, 17 a window), the standard error of the mean with the
   positions taken in batches of 1, 4, 16, 64 and 256 windows: 1 head
   0.0082, 0.0088, 0.0102, 0.0138, 0.0123; 4 heads 0.0082, 0.0087, 0.0100,
   0.0134, 0.0114; their difference, position by position, 0.0014, 0.0014,
   0.0016, 0.0018, 0.0022. Neighbouring windows are alike (a scene, its
   names): the error grows from one window to batches of 64 by 1.7 times,
   then the 12 batches of 256 are too few to say more. Taken at 64 windows:
   the test text's own sampling error of one model's score is 0.0138 bits,
   as large as the spread over seeds (sd 0.0158 and 0.0090): Bouthillier et
   al.'s finding that the data's sampling is a source as large as any. For
   the difference of two models on the same text it is 0.0018, against the
   spread of the seeds' differences, 0.0074: the comparison is limited by
   the seeds, not by the test text. (Miller's paired differences, on test
   positions instead of questions.)
5. seeds_needed at this run's spread (each arm's sd 0.0129, the pairs'
   0.0074), 95% and four times in five: a difference of 0.010 needs 28
   seeds a side independent, 7 paired; 0.026 (the one measured) 6 and 3;
   0.050 3 and 3.
6. The recorded run, read by the default (experiments/recorded/errorbars/:
   heads1/ and heads4/, seed0 to seed9, config.json, log.jsonl and
   summary.json with test_bits and test_sem; pairs.svg; output.txt):

       python3 -m experiments.errorbars seeds=10 out=experiments/recorded

   178 s by its own clock (01:02:11 to 01:05:10 on 2026-11-25, load 12 to
   19). Seeds 0 to 2 are the default's to the last digit. 1 head `3.431 +-
   0.01206` (3.412 to 3.445), 4 heads `3.406 +- 0.006721` (3.398 to
   3.418), t = -5.7; sems 0.0038 and 0.0021, intervals (t at 9 df, 2.26)
   3.4227 to 3.4400 and 3.4015 to 3.4112. The difference -0.0250: Welch
   -0.0343 to -0.0156 (width 0.0187), pairs -0.0319 to -0.0181 (width
   0.0138, 26% narrower), the bootstrap of the pairs -0.0304 to -0.0191; 4
   heads lower on 10 of 10 seeds. The verdict, as found: four heads of 16
   are better than one head of 64 at equal weights, by 0.025 bits per
   character (0.7%), beyond doubt at 10 seeds, either way of counting. The
   arms' correlation over seeds is +0.60, not the +0.97 three seeds showed:
   three points made pairing look worth far more than it is here (the
   3-seed paired interval, -0.044 to -0.0075, still held the 10-seed
   difference). Henderson et al.'s test on each arm, seeds 0 to 4 against 5
   to 9: 1 head t = -1.5, 4 heads t = -0.2: no split of these seeds looks
   like two methods (theirs, in RL, gave t = -9.1). seeds_needed for 0.025
   at the pairs' sd 0.0096: 4; drawn from the 10 (2000 draws each), n
   seeds gave a paired interval clear of 0 in 0.26 of draws at n = 2, 0.62
   at 3, 1.00 at 5 (draws of 5 from 10 overlap heavily: rough). At the
   10-seed spread, seeds_needed: 0.010 needs 16 a side independent and 10
   paired; 0.026 4 and 4; 0.050 3 and 3. With the test-set error of the
   difference (0.0018) beside the seeds' sd of it (0.0096), more test text
   would not have decided it sooner; more seeds did.
The default, seeds 0 to 2 trained and the record read: 56 s by its own
clock (57.5 s of wall clock) at load 11 to 12, timed back to back with the
other three defaults; 77 s at load 15 to 16 earlier (the scaling run going).
It trains 6 models of 4 blocks; 08.02's 3-seed default (15 runs, 9 of
them 4 deep) took 47 s at load 5 to 6, so a quiet machine should take
about 25 to 30 s. Not cut: the planner's rule cuts at 55 s with the load
under 6, not seen.

### 13.03 An evaluation you tried to fool

experiments/fooled.py, three parts.
1. Choosing by the test set. hold_back(10000, rng 0) cuts MNIST's test
   images into two random halves of 5,000 before anything runs. Drawn, not
   cut: in file order the first 5,000 are 8.21% wrong and the last 5,000
   4.80% (the 32 runs' average), so a cut would make the held-back half
   a different test. (MNIST's page, said to describe the two blocks, was
   not reachable to read; nothing here rests on it.) 32 runs of 13.01's
   network with Adam at 0.004 (its search's choice, rounded), 2 passes
   over the first 10,000 training images, differing only by seed (a
   search over a setting that does nothing is this). Test error, %: A
   `6.71 +- 0.52` (min 5.6, max 7.82), B `6.3 +- 0.438` (5.52 to 7.46):
   the halves differ by 0.4 points for
   every run alike (B is easier by chance). Of A's variance over the runs
   (0.2705), B shares 0.1791 (their covariance: the runs really differ);
   the rest, 0.0914 (sd 0.302), is the luck of A's images. A coin for each
   image at 6.7% wrong would give sd 0.354: the runs err on many of the
   same images, so a run's own luck on a test half is a little less than
   the binomial's. The best of k by A, expected over every way of drawing
   k of the 32 (best_of), against the average run: k = 2, 4, 8, 16, 32:
   gain on A 0.294, 0.538, 0.766, 0.969, 1.114 points; predicted from A's
   spread alone (normal_best(k) sd_A) 0.293, 0.535, 0.740, 0.918, 1.076;
   the same run's gain on B 0.198, 0.327, 0.413, 0.535, 0.778; lost 0.096,
   0.211, 0.353, 0.435, 0.336, against the luck's share predicted (gain
   times 0.0914 / 0.2705) 0.099, 0.181, 0.250, 0.310, 0.364. So the best
   of 32 looks 1.1 points better than the average run where it was chosen
   and is 0.78 better where it was not: about a third of a point of its
   lead is the test half's luck. As measured, k = 32's loss (0.336) is
   below k = 16's (0.435): at k = 32 every draw holds the single best run
   on A, which happens to be good on B too; the largest k rest on a few
   runs, the predicted column on all 32.
2. Leakage in images. exact_copies (a set of the training rows' bytes):
   MNIST 0 of 10,000, CIFAR-10 0 of 10,000. Twins: shrink (each channel
   averaged over pool x pool squares, centred, scaled to length 1;
   MNIST at full size, CIFAR-10 at 8 x 8), two_nearest (cosine distance,
   the nearest and second nearest training image), and the ratio test: a
   twin when the nearest is under half as far as the second nearest. A
   distance alone did not work: on raw pixels the nearest pairs in
   CIFAR-10 are no closer than ordinary ones (no test image within an RMS
   difference of 0.05 of a training image, 0..1 pixels; spike: a shifted
   copy is far in pixels), and in MNIST the nearest training digit of a
   test digit is at 0.030 at the least, 0.085 for the nearest tenth, 0.15
   for half, with no gap that marks copies off from look-alikes. The
   ratio asks for a training image far nearer than every other one.
   Found: MNIST 41 test digits with a twin (0.41%), CIFAR-10 346 (3.46%).
   By eye (spike: pairs drawn side by side): CIFAR-10's 53 with a ratio
   under 0.1 are every one the same photograph, shifted, cropped or
   re-coloured; of 48 drawn between 0.3 and 0.5 nearly all are (a few are
   two photographs of one model of car, or two ships), and between 0.5 and
   0.6 about half are. MNIST's are digits whose strokes match closely (the
   same shape of 2, 4 or 7), not copies of one scan; whether one person
   wrote both is not known here. With pool 4 on MNIST every test digit has
   near look-alikes (265 under 0.5, digits that are only similar): the
   pooling is chosen per data set, and the page should say so.
   Accuracy, the nearest training image's label (a classifier that only
   remembers): CIFAR-10 100.0% on the 346 with a twin, 41.3% on the rest,
   43.4% overall, of which 2.03 points come from the twins (Recht et al.'s
   arithmetic); MNIST 100.0% against 97.2% (0.01 points). Part 1's 32
   networks on MNIST: 96.4% on the 41 against 93.5% on the rest; they
   trained on the first 10,000 training images, so most twins' training
   copies were never seen: MNIST's twins are easy digits, and that is most
   of their lead. No network was trained on CIFAR-10 here (a minute of CPU
   does not fit beside the rest); Recht et al. report 99 to 100% for
   trained classifiers on their 800.
3. Leakage in text. Tiny Shakespeare split by position (data/
   shakespeare.py): of the test text's runs of k characters the training
   text has 47.59% at k = 8, 1.22% at 16, 0.00% at 32: no 32 characters of
   The Tempest are anywhere in the training plays. Cut instead into
   windows of 256 every 128 characters and a tenth drawn at random for
   testing (rng 0), 91.0% of a test window's characters are inside some
   training window: a model scored that way is scored on text it trained
   on. TinyStories: 100 of the 21,990 held-out stories are word for word
   among our 74,394 training stories (none of the first 2,000, which 09.04
   and 13.04 score on, so neither number moves), and the training stories
   repeat themselves 300 times. Our training stories are the first 64 MiB
   of a 1.9 GB file; the whole file was not searched.
Recht et al., the same and different. They built a second test set for
CIFAR-10 (and ImageNet) by the first one's recipe and scored dozens of
published models on both: the drops were large (3 to 15 points) and
followed a line in the original accuracy, which they read as a shift to
harder images, not as adaptive overfitting. Here the second set is a half
of the same test set drawn at random (no shift by construction), the
models are 32 seeds of one method, and the choice among them is made by
the test set on purpose: what is measured is the adaptive part alone, and
it is about a third of a point. Their near-duplicates were judged by eye
(same object, same pose; about 800 in CIFAR-10's test set) and the
models were trained classifiers (99 to 100% right on them); ours are the
ratio test's 346 and a classifier that only remembers. By their
arithmetic the twins are worth at most 0.6 points to a 93% model; to our
43% remembering classifier, which gets the rest right far less often,
2.0 points.

### 13.04 Scaling: predicting a model you have not trained

experiments/scaling.py: 08's GPT at one depth, 4 blocks of 4 heads, the
width varied (so N is about 48 W^2), on TinyStories with 09.04's tokens (a
vocabulary of 4096); every size trained for the same number of tokens by
language.train (AdamW, weight decay 0.1 on the matrices and embeddings,
warmup then cosine to 0, clipped to 1; one learning rate for every size),
the same seeds (so one seed draws the same batches for every width), and
scored on the first held-out stories with window_bits (each token with a
quarter of the window or more before it), in bits per token, with bits per
byte beside it (09.04's per_character). counted gives N as Kaplan et al.
count it: every weight but tokens.weight and positions.weight (biases and
layer norms are counted: 3.4% of N at width 32, 0.9% at 128, 0.4% at
256); 12 L W^2 is printed beside it. predict fits lab.power_law through
every run of every width but the largest (bits against N, seeds as points)
and gives power_interval's 95% range for the mean of as many runs as the
largest has; then the largest's runs beside it. Both ways of counting:
weights as the paper counts them, and every weight (the vocabulary's
4096 x W embedding included).

Spike, what I tried (load 10 to 13). Step times on this CPU, windows of 256,
batches of 32, 4 blocks: width 32 82 ms (1 head of 32), 48 88, 64 119, 96
174, 128 219, 192 302, 256 408 (heads = width / 32); windows of 128,
batches of 64 (the same tokens): 32 64, 64 93, 128 163, 192 253. The small
widths cost nearly as much as the larger ones: the vocabulary's 4096 scores
and the attention's T x T tables do not shrink with the width. Then 300
steps of each, one seed, lr 0.002 (5 to 74 s each): bits per token 6.554,
5.926, 5.729, 5.386, 5.214, 4.814 at widths 32, 48, 64, 96, 128, 192: a
fair straight line on log-log axes (slope -0.08 to -0.10). From those the
recorded run's settings: widths 32 to 128 to fit, 256 to predict (4 times
the largest fitted N), 800 steps (6.55 million tokens each, 0.39 passes
over the 16.7 million: no token seen twice by any model, so not limited by
repetition), 3 seeds of each fitted size, 2 of the largest, an estimated
37 minutes at load 11. Not tried: other learning rates per size (the
paper's own rule, its D.1, gives smaller rates to larger models; it does
not say which logarithm), other depths, windows of 128, more steps.

(That spike gave each width width / 32 heads; the recorded run has 4 heads
at every width, which costs the small widths more: width 32 took 100 to
110 s for 800 steps at load 15, about 130 ms a step.)

The long run, recorded in experiments/recorded/scaling/ (width<W>/seed<k>/
config.json, log.jsonl with the held-out windows' curve every 50 steps,
summary.json; fit/seed0/summary.json, both fits and predictions;
curves.svg, every run's held-out bits against the tokens seen, log axes;
fit.svg, the runs, the line, the interval and the largest's runs;
output.txt, what it printed). No weights are written by scaling.py.

    python3 -m experiments.scaling "widths=[32,48,64,96,128]" largest=256 context=256 batch=32 steps=800 lr=0.002 warmup=50 every=50 seeds=3 largest_seeds=2 held=64 held_stories=2000 out=experiments/recorded

3054 s by its own clock (00:11:00 to 01:01:55 on 2026-11-25), load 10 to
21 (three other agents training; the run's 10 threads fighting for
cores): widths 32 and 48 100 to 135 s a run, 64 114 to 167, 96 176 to 199,
128 181 to 228, 256 356 and 417. At the spike's load of 11 the estimate
was 37 minutes. fit.svg was drawn again afterwards from the summaries,
after plot() was changed to draw the line a little past the largest (the
held-back points sat on the frame's edge); nothing else was touched.

Bits per token on the first 2,000 held-out stories (395,221 tokens; bits
per byte beside them):
- width 32, N 50,880 (all weights 190,144): `5.803 +- 0.03711` (5.763 to
  5.836); 1.445 per byte
- 48, N 113,184 (322,080): `5.392 +- 0.02255`; 1.342
- 64, N 200,064 (478,592): `5.146 +- 0.04659`; 1.281
- 96, N 447,552 (865,344): `4.726 +- 0.04093`; 1.177
- 128, N 793,344 (1,350,400): `4.441 +- 0.01043`; 1.106
- 256, N 3,159,552 (4,273,664), held back: `3.925 +- 0.01081` (3.917,
  3.933, 2 seeds); 0.977 per byte (09.04's long run, 4 blocks of 8 heads
  at width 256 for 4000 steps: 0.7367).
The fit, weights counted as the paper counts them, 15 runs: alpha =
0.0971, standard error 0.0021; N_c = 10^12.6 (bits, our tokens: no
meaning beside the paper's 8.8 x 10^13, as the paper says of its own);
scatter about the line 0.0078 in ln bits. The prediction for width 256,
made from the five smaller widths (and computed by hand at 00:49:25, while
width 256's first seed was training: 3.9038): 3.904 bits per token, 95%
interval for the mean of 2 runs 3.836 to 3.973. Trained: 3.925, inside,
0.5% above the prediction. The local exponents between neighbouring
widths, 0.092, 0.082, 0.106, 0.109 and, from 128 to 256, 0.089: no bend
either way, the last a little flatter than the fit, which is the 0.5%.
Every weight counted (the 4096 x W embedding too): alpha 0.1360 (standard
error 0.0024), scatter 0.0064 (closer to its points than the paper's way),
predicted 3.803 (3.746 to 3.861) and trained 3.925: outside, 3.2% above.
The embedding is 73% of all weights at width 32 and 26% at width 256, so
counted in, it makes the small models look larger than they compute and
bends the line: the paper's figure 6 reason for leaving it out, held here
by the prediction it spoils, not by the fit's scatter (which is smaller).
Every curve in curves.svg is still falling at the end: no size was
trained to convergence. The training batch and the held-out windows end
level (width 256: 3.895 and 3.920 bits; every token seen once).

What held of the paper, and what a laptop does not meet:
- A power law in N fits at this scale: five sizes over 1.2 decades
  (Kaplan et al.: six decades), scatter under 1%, and it predicted a model
  4 times larger than any it was fitted to, within its interval.
- The exponent is 0.097 against the paper's 0.076, and the two are not the
  same measurement: theirs is for models "trained to convergence on
  sufficiently large datasets" (2.5 x 10^5 steps of 512 x 1024 tokens,
  on 22 billion tokens, early-stopped), ours for every size stopped at the
  same 6.55 million tokens, far from convergence (every curve still
  falling), on 16.7 million tokens of children's stories with a vocabulary
  of 4096. At a fixed number of steps the paper's own law is equation
  1.6, L(N, S) = (N_c / N)^alpha_N + (S_c / S_min)^alpha_S: a power law
  plus a constant, which on log-log axes flattens at large N (not seen
  over our range); and larger models are "more sample-efficient", so at
  equal tokens they are further ahead early in training than at
  convergence. Not data limited as the paper means it (nothing was seen
  twice, so nothing could be overfitted; their rule for training to
  convergence without overfitting, D >~ 5 x 10^3 N^0.74, asks for 3.2 x
  10^8 tokens at our largest N, 19 times the 16.7 million we have). One
  learning rate for every size (theirs fell with size, their D.1), one
  depth (theirs varied both), windows of 256 (theirs 1024).
- The paper's precise exponent is not checked (it says its constants
  "depend on the vocabulary size and tokenization"); what is checked is
  the use: a line through small models predicts a larger one.

The default run (no download beyond TinyStories): widths 16, 24 and 32 to
fit and 48 to predict, windows of 64, 120 steps of 32 (245,760 tokens), lr
0.003, 2 seeds each; scored on the first 200 held-out stories.

The default's own sizes at 120 steps barely leave the start (bits per
token 8.59, 8.41, 8.13 at widths 16, 24, 32; 2 seeds each, sds up to
0.14): alpha 0.0399 (standard error 0.0090) the paper's way, 0.0648 with
every weight; width 48 predicted 7.909 (7.559 to 8.275) and trained
`7.865 +- 0.1937`, inside either way: the interval is wide because two
seeds of so short a run scatter by 0.1 to 0.2 bits. It shows the method;
the law is the recorded run's, which the default reads and prints (part
3). 44 s by its own clock (45.1 s of wall clock) at load 12, back to back
with the other defaults; reading the record adds about a second.

### Recorded runs, and the hour

- 13.04, experiments/recorded/scaling: 3054 s (50 min 54 s), 00:11:00 to
  01:01:55 on 2026-11-25, load 10 to 21.
- 13.02, experiments/recorded/errorbars: 178 s, 01:02:11 to 01:05:10, load
  12 to 19.
Together 3232 s, 53 min 52 s of wall clock, inside the hour, most of it
13.04's as the design asked. 13.01 and 13.03 have none (their defaults
are the whole experiment). Both records ship their config, log and
summary for every run, their figures and output.txt; no weights (neither
script writes any). 228 KB and 252 KB.

### The defaults' times

Back to back at 01:05 to 01:07 on 2026-11-25, load 11 to 12.5 (three other
agents' work), by their own clocks (wall clock in brackets): baseline 9 s
(9.9), errorbars 56 s (57.5), fooled 16 s (16.8), scaling 44 s (45.1).
Earlier, at load 14 to 16 with the scaling run going: baseline 14 to 26
s (8 or 16 trials), errorbars 77 s, fooled 23 s, scaling 37 s (load 10).
On a quiet machine errorbars and scaling should take about half of these;
both are under the planner's rule (a cut at 55 s with the load under 6).
The same digits on every run of each.

### What held, and what did not

- 13.01: the design's point held at this size: the hurried comparison
  (Adam's rate searched, SGD's taken from the docs) makes a clear win, 8.4
  points of test error, t = +21; the same search for both leaves 0.81
  points, t = +2.7, a tie by the rule written first. Most of the hurried
  gap is the baseline's missing search: a search of 1 trial leaves SGD 6.5
  points behind on validation, of 8 trials 2.5 (best_of). 03.03's tie
  (training cost, 3 passes over 60,000) is not contradicted: Adam leads by
  0.8 points here after 2 passes over 10,000 images, without 3 standard
  errors. Henderson et al. ask for "standard hyperparameter searches" of
  baselines and the playbook that "the baseline should also have its
  learning rate equally well tuned": both held.
- 13.02: 08.02's doubtful result is real: four heads beat one at equal
  weights by 0.025 bits per character, t = -5.7 at 10 seeds, the paired
  interval -0.032 to -0.018, lower on every seed. 08.02's t = -2.4 at 3
  seeds was a true difference that 3 seeds could not show unpaired; paired,
  3 seeds already showed it (seeds_needed: 3 to 4 paired, 4 to 6
  independent). Bouthillier et al.'s order of the sources held for one
  model's score (the test text's sampling error, 0.0138, as large as the
  seeds' spread, 0.007 to 0.016) and Miller's pairing for a difference
  (0.0018 against 0.0096); Henderson et al.'s split of one method's seeds
  into "different" halves did not appear here (t = -1.5 and -0.2).
- 13.03: choosing by the test set moves a score by about a third of a
  point of MNIST error among 32 runs that differ only by seed, as their
  own spread predicts: small beside Recht et al.'s 3 to 15% drops on
  CIFAR-10, which they put down to harder images, not to adaptivity; at
  this scale ours agrees that test-set reuse alone costs little.
  Near-duplicates: CIFAR-10 has 346 test images (3.5%) with a twin in
  training by our rule (Recht et al., by eye and a looser rule: about 800,
  8%); they inflate a remembering classifier's accuracy by 2.0 points;
  MNIST 41 (0.4%), and no exact copies in either. TinyStories' held-out
  file has 100 stories word for word in our training stories, none among
  the 2,000 our scores use.
- 13.04: a power law in N held at laptop scale, and its prediction of a
  model four times larger landed inside the interval (3.925 against 3.904,
  +0.5%); counted with the embeddings it missed by 3.2% (the paper's figure
  6 held, by prediction). The exponent, 0.097, is not the paper's 0.076,
  and is not the same quantity (fixed tokens, far from convergence; the
  paper's equation 1.6 is the law for that case).

### Departures from the design, and why

- 13.01 searches each optimiser's learning rate only (SGD's momentum at
  0.9 and Nesterov's form, Adam's betas at their defaults, as 03.03 had
  them), with plain random draws, not the playbook's quasi-random ones (in
  one dimension it allows a grid; random draws keep any n of the trials a
  fair sample for best_of). The hurried baseline is the rate of PyTorch's
  own example, lr 0.01, momentum 0.9 (with Nesterov's form, as every SGD
  arm here). The comparison is test error after 2 passes over 10,000
  images, not 03.03's training cost after 3 over 60,000: a minute holds 31
  runs of this. 03.03's own claim stays where 03.03 left it.
- 13.01 and 13.03 use MNIST as designed; no claim of module 08 was used
  instead (08.02's heads go to 13.02, which needs them).
- 13.02's verdict rests on a recorded run of 10 seeds a side, not more:
  the hour was 13.04's (see Recorded runs). The default trains seeds 0 to
  2 (08.02's page ran 3) and reads the record.
- 13.02's test-set error is measured by batches of consecutive windows
  (batch_sem), Miller's clustered errors with the clusters made from the
  text's order, since the test text has no questions to group.
- 13.03's second held-out set is half of MNIST's test images drawn at
  random before any run, not images held back from training (the design
  allowed either; this keeps the training set 13.01's).
- 13.03's near-duplicates are found by the ratio test on shrunk, centred
  images, not by Recht et al.'s l2 and SSIM neighbours checked by eye;
  plain distances did not separate copies from look-alikes (spike, above).
  No network was trained on CIFAR-10 for the twins' accuracy (a remembering
  classifier, the nearest image's label, stands in); MNIST's twins are
  scored by part 1's networks too. The text part adds TinyStories' repeated
  stories, which the design did not name.
- 13.04 varies the width only (4 blocks of 4 heads), one learning rate for
  every size, 800 steps; it took 51 minutes at load 10 to 21, against an
  estimate of 37 at load 11; with 13.02's recorded run the module's
  recorded runs took 53 min 52 s, inside the hour, with less to spare than
  planned. 13.02's record is 10 seeds a side for that reason.
- lab/stats.py's t_quantile keeps its answers (functools.lru_cache): the
  same few quantiles are asked for thousands of times by a test's
  simulations and by seeds_needed, and each costs a Newton's method over
  Simpson's rule (5 to 30 ms).

### Tests (module 13)

`./learn test research 13`: all 4 pass (13.01 12.7 s, 13.02 53.1, 13.03
12.4, 13.04 40.0 in the whole suite's run, load 11 to 14). Each runs its
exact checks first (inside()), then its experiment:
- 13.01: best_of against every draw of n of N counted by hand (N up to 7,
  with and without a reported number); draw_rates seeded, every rate in
  its range, the same u's in each range; run_one the same twice, another
  optimiser other numbers, errors a share of the images, a log row a pass;
  verdict's three outcomes. Then (MNIST) baseline with seeds=3: the
  hypothesis printed first; the hurried gap over 3 points and over twice
  the fair one, with t of 3 or more; the docs' rate worse than SGD's tuned
  one; the best-of table's 8 rows, validation never rising with n; a tiny
  run twice, the same bytes.
- 13.02: sem; t_quantile against the t table (seven values) and, with
  scipy, t_density, t_cdf and t_quantile at whole and fractional degrees of
  freedom, interval against t.interval, difference against ttest_ind
  (Welch) and ttest_rel's intervals; Welch's degrees of freedom written
  out; a paired difference of unequal arms refused; bootstrap against the
  same draws taken by hand, and against mean +- 1.96 sem on 4,000 normal
  numbers; seeds_needed against 20,000 simulated experiments at n and at
  n - 1, four cases (two of them this lesson's spreads); batch_sem on an
  AR(1) series of known correlation; position_bits' length and mean against
  window_bits at three spans. The recorded run's files (both arms, 10
  seeds, configs equal but the seed, logs, output.txt) and its verdict (the
  paired interval clear of 0). Then the default: 08.02's 3.433 and 3.407
  within 0.01, the same start for both arms, the paired interval narrower
  than Welch's, the difference's test-text error under a third of one
  model's, neighbouring windows moving together; a tiny run twice.
- 13.03: normal_best against 0, 1 / sqrt(pi), 3 / (2 sqrt(pi)) and 200,000
  draws of 10; hold_back disjoint, covering, seeded; shrink's length-1 rows
  and a brighter copy the same, against pooling written out; two_nearest
  against a full search; exact_copies and the twin rule on 500 blocky
  images with 3 planted copies, 4 shifted by a pixel and 20 strangers (the
  7 found, the 20 not); shared_grams against a set of tuples. Then (MNIST,
  CIFAR-10 and TinyStories: "missing:" without each) fooled with 8 runs:
  the best of 8 by A ahead on A by more than on B; no exact copies; CIFAR-
  10's twins between 100 and 800; twins right more often than the rest;
  no shared run of 32 in Tiny Shakespeare, over 80% shared by overlapping
  windows; held-out stories found in training; a tiny run twice.
- 13.04: power_law exact on made points, alpha's standard error the
  spread of 3,000 noisy fits' alphas (within 10%), power_interval covering
  the law's value and the mean of 2 new runs 95% of the time (within 1.5
  points), a narrower level inside a wider one; counted for GPTs with and
  without positions, equal to 3 (12 W^2 + 13 W) + 2 W, and within 1% of 12
  L W^2 at width 256; predict on made rows (inside, and outside when the
  largest is 20% worse); read giving back what lab.Run wrote. The recorded
  run (every width and seed, configs, curves, summaries with the tokens,
  the loss falling with width, the fit re-made from the summaries, the
  prediction inside and nearer than with every weight). Then (TinyStories)
  the default: both predictions printed, the record read; a tiny run
  twice. LEARN_RERUN_LONG=1 reruns 13.02's and 13.04's records from their
  configs (about 3 and 50 minutes).
`./learn check-skeleton research 13` ok, 6 s (13.01 fails at best_of,
13.02 at sem, 13.03 at normal_best, 13.04 at power_law).
The whole track (modules 00 to 09, 13 and 14; three other agents
training): `./learn test research` 52 tests, all pass, 18 min 29 s at load
11 to 27 (01:15:21 to 01:33:50). `./learn check-timeline research` ok, 5
min 51 s at load 10 to 11; the project has 195 files at 13.01, 258 at
13.02 (63 of them the recorded errorbars run), 259 at 13.03 and 317 at
13.04 (57 the recorded scaling run), 320 to 392 at 14.01 to 14.04; 06.04
still 98, 07.02 145, 08.04 170, 09.04 194. At each lesson from 13.01 on
the timeline runs the module's short settings (fooled with n_test=500, so
its twin search reads 500 test images). `./learn selftest` ok (269 tests).
`./learn check` reports exactly twelve problems, `research/13.0N` and
`research/14.0N: test has no lesson doc` and four `kilo/08.0N` of the
same kind (another track's, on master); nothing else.

### For the harness, and what a page writer meets

- No harness change. track.py's module-13 part is the last block of the
  file: the four experiments in EXPERIMENTS with short settings for the
  timeline, DATASET_OF (baseline and fooled MNIST, errorbars none, scaling
  tinystories), and the two recorded folders first in FILES_FROM with
  their DATA lines.
- Session needs=: 13.01 needs="torch" (MNIST is a download, as for 03.01 to
  06.01, not a tool); 13.02 needs="torch"; 13.03 needs="torch cifar10
  tinystories" (without them fooled.py prints a line per part it skips,
  so the page's output would differ); 13.04 needs="torch tinystories".
- lab/stats.py gains numpy (bootstrap) and statistics.NormalDist
  (seeds_needed, normal_best) as one-line @from 13.02 imports, and
  functools for t_quantile's cache; its docstring gains one line per
  lesson, each with its marker, so at 00.03 the file is as it was.
- Region titles that are ordinary words (lead-ins match them, case
  aside): interval, difference, bootstrap (13.02), shrink (13.03),
  counted, predict (13.04). A `### ` heading in How it works that says
  "the difference" or "an interval" is pulled into The code; word such
  headings without them.
- 13.02's and 13.04's defaults read their recorded runs, which the project
  has from their lessons (FILES_FROM), so verify replays them; 13.04's
  default also trains its small sizes. Neither recorded run is rerun by a
  test unless LEARN_RERUN_LONG=1.

### For module 15: the tools on a learner's own experiment

- The fair search (13.01): write the hypothesis and the rule that decides
  it before any run (baseline.py's HYPOTHESIS and RULE). Give every arm the
  same search: draw_rates(ranges, trials, rng) with one range per arm, as
  wide on a log scale for each, every trial on one seed, chosen on
  validation; then the chosen setting of each arm on fresh seeds, reported
  on test. best_of(val_errors, n, test_errors) says what n trials bought
  each arm, so a reader can see whether the search was enough.
- The paired comparison (13.02): run both arms with the same seed for
  each pair (torch.manual_seed(seed) before building, run.rng for the
  data order: models of the same shapes start from the same weights), then
  lab.difference(a, b, paired=True) for the interval, beside
  lab.difference(a, b) to show what pairing bought. Report the interval,
  not only t: with 3 seeds the t to beat is 4.30.
- How many seeds (13.02): from a pilot of 3 to 5 seeds, the sd of the
  paired differences and the smallest difference worth finding,
  lab.seeds_needed(size, sd, paired=True); run that many before deciding,
  and say in the write-up that the number was fixed first.
- The second held-out set (13.03): hold_back(n, rng) on the test set (or
  on the validation set) before any run; choose on one half, report on
  the other. If many runs were compared, the gain the chosen one shows on
  the half it was chosen on is lab.normal_best(k) times the runs' sd, and
  part of it is luck the other half will not repeat.
- Leakage (13.03): before reporting a score on a new data set, count
  exact copies (exact_copies) and twins (shrink, two_nearest, the ratio
  test) between its training and test parts, and the shared runs of a
  text split (shared_grams); report the score with and without them.
- Scaling (13.04): for a claim that "bigger is better", train three or
  more sizes for the same tokens, several seeds each, and say which
  weights are counted; power_law and power_interval give the exponent with
  its error and what the next size should score, before it is trained.

### Checked, and not checked

Checked: every statistic against scipy 1.17.1 (sem, the t density,
distribution and quantiles at whole and fractional degrees of freedom,
Student's and Welch's intervals, the paired interval) and against the t
table and the formulas written out, so the tests mean something without
scipy; best_of against every draw counted by hand; seeds_needed against
20,000 simulated experiments at its n and one fewer; power_interval's
coverage over 3,000 made experiments (95.0% within 1.5 points); batch_sem
on a series of known correlation; the twin rule on planted copies and
shifted copies; position_bits against window_bits; every quote above
found again in the source's text. CIFAR-10's twins were looked at by eye
(spike: pairs drawn side by side at three bands of the ratio).
Not checked: quasi-random search (the playbook's) against the random
draws used; a trained network's accuracy on CIFAR-10's twins; the whole
TinyStories file for held-out stories (only our 64 MiB); per-size learning
rates or other depths for 13.04, and whether its exponent moves with the
steps (one budget, 800 steps, was run); the paper's precise exponent at
convergence (not reachable on a laptop); Linux. Schulman's guide was not
read.

## Module 15: your own result

Built by one agent on 2026-11-25, code, recorded runs, lessons and art, on
the reference machine above (Apple M4 Pro, Python 3.12.7, numpy 2.4.3,
PyTorch 2.10.0, 10 threads by default), shared all the while with other
agents' work (modules 11 and 12's code, module 13's lessons): load average
8 to 19. Every time below says its load. The module does one piece of
research whole, on the question 08.03 left: how much are learned positions
worth as blocks are added, and how many blocks does a GPT without them
need to match one with them?

### The files

```
experiments/question.py  15.01   QUESTION, BEFORE (08.03's numbers), RELATED, PREDICTIONS (7), SMALLEST, LEVEL,
                                 POWER, ARMS; pair, trained, judge, budget, read_runs (regions); rule_text
                         15.02   choose, gaps (regions); results (an @from block): depth.py's runs read back
experiments/pilot.py     15.01   the pilot (no regions: FILES_FROM)
experiments/depth.py     15.02   search, Wider (regions); widen, extra_units, table, draw, main
experiments/paper.py     15.03   defaults, command, abstract, verdicts (regions); gather, paper, surprises, main
experiments/recorded/pilot/      15.01's recorded pilot (depths 1 and 8, 4 pairs; output.txt)
experiments/recorded/depth/      15.02's recorded experiment (output.txt, bits.svg, gap.svg)
experiments/recorded/followup/   15.02's follow-up past the top of the search (depth/, output.txt)
experiments/recorded/paper/      paper.txt, as paper.py wrote it from the two records
tests/1501_... to 1503_...       one a lesson
```

question.py is shared code with no main, as 14.01's predictions.py is:
an experiment never imports another, so what pilot.py, depth.py and
paper.py share lives there (the predictions, the pairing, the scoring,
the readers, the comparison). models/gpt.py and experiments/language.py
are not changed: the two arms are GPT(V, 32, layers, 4, 64,
positions=False) and positions=True, trained by language.train.

### What was read, at the source

Fetched on 2026-11-25 with curl into a scratch folder and read as text
(the HTML with its tags taken out; each PDF through pdftotext); every quote
on the pages and in question.py was found again in that text by search.

- Richard Hamming, "You and Your Research", the transcription of the
  Bellcore colloquium of 7 March 1986 at
  https://www.cs.virginia.edu/~robins/YouAndYourResearch.html. Read: the
  talk whole (not the question period after it). Used: "Most great
  scientists know many important problems. They have something between 10
  and 20 important problems for which they are looking for an attack.";
  "It's not the consequence that makes a problem important, it is that you
  have a reasonable attack."; "If you do not work on an important problem,
  it's unlikely you'll do important work."; Friday afternoons, "Great
  Thoughts Time"; on selling, "it is not sufficient to do a job, you have
  to sell it", "You have to learn to write clearly and well so that people
  will read it", "The tendency is to give a highly restricted, safe talk;
  this is usually ineffective." Not used: the parts on drive, courage, the
  door open or shut, age.
- John Schulman, "An Opinionated Guide to ML Research" (posted
  2020/01/24), http://joschu.net/blog/opinionated-guide-ml-research.html,
  whole. Used: "Your ability to choose the right problems to work on is
  even more important than your raw technical skill."; idea-driven against
  goal-driven research and "One major downside of idea-driven research is
  that there's a high risk of getting scooped or duplicating the work of
  others. Researchers around the world are reading the same literature,
  which leads them to similar ideas."; "Aim High, and Climb Incrementally
  Towards High Goals" ("Will this be a 10% improvement or a 10X
  improvement?"); "Keep a Notebook, and Review It". The quotes are written
  in ASCII: the page has curly apostrophes.
- Simon Peyton Jones, "How to Write a Great Research Paper". The page the
  outline links (microsoft.com/en-us/research/academic-program/
  write-great-research-paper/) refused an automated client (a page
  titled "Microsoft" with no content); so did the PDF of the slides at
  microsoft.com/en-us/research/uploads/prod/2016/07/How-to-write-a-great-
  research-paper.pdf. Read instead: his own page,
  https://simon.peytonjones.org/great-research-paper/ (which links the
  same PDF and PPT), and the PDF itself through the Wayback Machine
  (web.archive.org/web/2023id_/<that URL>, 513,948 bytes), whole: the
  slides' text, 352 lines. Used: "Writing papers is a primary mechanism
  for doing research (not just for reporting it)"; "Do not be
  intimidated" and "Write a paper, and give a talk, about any idea, no
  matter how weedy and insignificant it may seem to you"; one "ping";
  the structure (Title (1000 readers), Abstract (4 sentences, 100
  readers), Introduction (1 page, 100 readers), The problem, My idea, The
  details, Related work (1-2 pages, 10 readers), Conclusions and further
  work); "Use an example to introduce the problem"; "Contributions should
  be refutable"; no "rest of this paper is..."; related work later ("No
  related work yet!"); "Be generous to the competition"; "Acknowledge
  weaknesses in your approach"; "Use the active voice" ("We ran 34 tests"
  against "34 tests were run"). The video was not watched.
- The question's literature, each PDF from arxiv.org/pdf/<id>:
  - Haviv, Ram, Press, Izsak and Levy (2022), arXiv 2203.16634 (08.03's
    paper, read again for depth): table 2 (NoPos against learned at 125M,
    350M, 760M, 1.3B: 22.15/22.04, 16.87/16.84, 14.29/14.21, 13.10/13.05;
    "Smaller models benefit from fixed, non-parametric positional
    encodings (Sinusoidal and ALiBi), but these performance gaps diminish
    as the models scale up"), table 5's sizes (12 layers at 125M, 24 at
    350M to 1.3B), section 5 and figure 2 (the probe: no position in the
    first layer, "it becomes position-aware within four layers"), section
    9, Limitations.
  - Irie, Zeyer, Schlueter and Ney (2019), "Language Modeling with Deep
    Transformers", Interspeech 2019, arXiv 1905.04226: the abstract,
    section 1, section 7 (7.1 to 7.3) and table 9: models (L, 2048, 512, 8)
    at L = 12, 24, 42 on LibriSpeech's word-level text, perplexity after 5
    epochs, train/dev/test: sinusoidal 61.8/63.1/66.1 against none
    58.0/60.5/63.4 (12 layers); 55.6/58.0/60.8 against 52.7/56.6/59.2
    (24); 51.2/55.0/57.7 against 50.5/54.2/56.8 (42). "we experimentally
    show that the positional encoding is not needed for multi-layer
    autoregressive self-attention models"; without positions the first
    layer "learns to focus on the new input token". Their comparison is
    against sines and cosines, not learned positions.
  - Kazemnejad, Padhi, Natesan Ramamurthy, Das and Reddy (2023), "The
    Impact of Positional Encoding on Length Generalization in
    Transformers", NeurIPS 2023, arXiv 2305.19466v2: the abstract and
    section 5.1, theorem 1 ("the first layer of f_theta can recover
    absolute positions [1, . . . , T + 1] in the hidden state H(1)"; the
    input starts with <bos>) and theorem 2 (later layers can then
    implement relative positions). Their models are about 107M weights;
    not read: their experiments' details, the appendices.
  - Chi, Fan, Chen, Rudnicky and Ramadge (2023), "Latent Positional
    Information is in the Self-Attention Variance of Transformer Language
    Models Without Positional Embeddings", ACL 2023, arXiv 2305.13571: the
    abstract only.
  - Zuo, Guerzhoy and Guerzhoy (2024), "Position Information Emerges in
    Causal Transformers Without Positional Encodings via Similarity of
    Nearby Embeddings", COLING 2025 (its arXiv comment), arXiv 2501.00073:
    the abstract and the first paragraphs of the introduction only.
  The search that found them (2026-11-25, three web searches: "transformer
  language model without positional encoding number of layers depth NoPE
  causal mask"; Irie et al.'s title; "NoPos NoPE shallow transformer few
  layers perplexity gap learned positional embedding ablation by number of
  layers"; and arXiv's own pages). Found: comparisons at 12 layers and
  more (Irie et al., Haviv et al.), theory for the first layers
  (Kazemnejad et al.), mechanisms (Chi et al., Zuo et al.). Not found: the
  gap block by block from one block, in a small model, at a fixed budget.
  A few searches are not a survey; 15.01 and the paper say so.
- The Deep Learning Tuning Playbook (Godbole, Dahl, Gilmer, Shallue,
  Nado), README.md at commit 7554a51f5d30 (2024-06-13), the sections
  "Identifying scientific, nuisance, and fixed hyperparameters" ("The
  learning rate is a nuisance hyperparameter because we can only fairly
  compare models with different numbers of hidden layers if the learning
  rate is tuned separately for each number of layers (the optimal
  learning rate generally depends on the model architecture)") and
  "Identifying bad search space boundaries" ("If the best points cluster
  towards the edge of a search space (in some dimension), then the search
  space boundaries might need to be expanded until the best observed point
  is no longer close to the boundary."), the reason for the follow-up.

### 15.01 Choosing a question a laptop can answer

experiments/question.py was written first and committed (31d3c6a, 01:58:23
on 2026-11-25) before the pilot or any run that scored a model; the only
run before it was a timing script outside the project (40 steps of each
model at each depth, printing milliseconds and weight counts, no bits). It
holds the question, 08.03's numbers (BEFORE), what the search found
(RELATED, five papers), seven predictions with their rules, SMALLEST =
0.02 bits (the smallest gap worth finding), LEVEL 0.95, POWER 0.8, and the
shared code. The rules: "largest" and "falls" by the means; "about" within
a factor of 2 by the mean; "above" by the paired interval (held / did not
hold / not settled); "clear" held only if the paired interval is above 0;
"worse" by Welch's interval (none at the deepest against learned at 4);
"closes_under" by the means.

The two arms of one seed (pair): GPT(V, 32, layers, 4, 64,
positions=False) built after torch.manual_seed(seed), the same with
positions=True built after the same seed, then every weight of the first
copied into the second (load_state_dict strict=False; the only missing key
is positions.weight, asserted). Without the copy the two would differ in
every block: positions.weight is drawn between tokens.weight and the
blocks in GPT's start loop. The batches are paired by the seed already
(run.rng). Measured that dropout 0 draws nothing from torch's generator
(F.dropout with p = 0 leaves the state unchanged), so the training adds no
other randomness.

The pilot, recorded (experiments/recorded/pilot):

    python3 -m experiments.pilot "depths=[1,8]" seeds=4 out=experiments/recorded

157 s by its own clock (01:59:24 to 02:02:02 on 2026-11-25), load 8 to 11.
At 08.03's rate 0.003, 300 steps, validation bits per character (each
character with 16 or more before it), 4 pairs (seeds 0 to 3):
- 1 block: none `3.486 +- 0.004904` (3.481 to 3.49), learned `3.336 +-
  0.03574` (3.291 to 3.371); the gap `0.149 +- 0.0315` (0.12 to 0.191);
  2.7 s a run.
- 8 blocks: none `3.386 +- 0.0109`, learned `3.354 +- 0.007017`; the gap
  `0.032 +- 0.00643` (0.0224 to 0.0362); 16.9 s a run.
The largest sd of a depth's gaps, 0.0315 (one block, nearly all of it the
model with positions), gives seeds_needed(0.02, 0.0315, paired) = 22
pairs; at eight blocks' 0.0064 it would be 3. Unpaired, at the largest sd
of one arm (0.0357), 52 a side. The budget at those times: 4 rates on one
seed and 22 pairs at depths 1, 2, 4, 6, 8, and 22 runs of the control at 4
blocks, about 43 minutes. The rule (the largest spread of any depth) was
in pilot.py before it ran; it was followed, though a rule per depth would
have asked far fewer pairs of the deep models (15.01's Decide the
boundary).

### 15.02 The experiment, and the result you did not expect

The recorded experiment (experiments/recorded/depth: search-blocks<d>-<arm>-lr<r>/seed0, blocks<d>-<arm>/seed1 to
seed22, control-blocks4-wider/seed1 to seed22; output.txt, bits.svg, gap.svg):

    python3 -m experiments.depth "depths=[1,2,4,6,8]" "rates=[0.0015,0.003,0.006,0.012]" seeds=22 steps=300 every=100 control=4 out=experiments/recorded

2817 s by its own clock (02:03:42 to 02:50:39 on 2026-11-25), load 9 to 19
(other agents training; 2.2 to 2.5 minutes a seed at load 15 to 19, about
1.7 at load 11). The pilot's estimate, 43 minutes at load 8 to 11. 282
runs: 40 of search (seed 0, validation only), 220 of pairs (seeds 1 to
22), 22 of the control. Each model at each depth kept the rate with the
lowest validation bits; the choices (none, learned): 1 block 0.006, 0.006;
2 blocks 0.012, 0.012; 4 blocks 0.012, 0.012; 6 blocks 0.012, 0.006; 8
blocks 0.012, 0.012: 7 of 10 at the top of the range.
Test bits per character (each character with 16 or more before it), 22
pairs; the gap none minus learned with its paired 95% interval (Welch's on
the same runs beside it):
- 1 block: none `3.484 +- 0.003809`, learned `3.196 +- 0.0227`; gap 0.2881
  (0.2781 to 0.2982; Welch 0.2780 to 0.2983); learned lower on 22 of 22;
  on validation 0.2922.
- 2 blocks: none `3.435 +- 0.009087`, learned `3.164 +- 0.03498`; 0.2707
  (0.2553 to 0.2862); 22 of 22; validation 0.2773.
- 4 blocks: none `3.392 +- 0.01759`, learned `3.191 +- 0.01914`; 0.2013
  (0.1903 to 0.2123); 22 of 22; validation 0.2062.
- 6 blocks: none `3.391 +- 0.01384`, learned `3.249 +- 0.01772`; 0.1412
  (0.1305 to 0.1520); 22 of 22; validation 0.1401.
- 8 blocks: none `3.384 +- 0.01204`, learned `3.26 +- 0.021`; 0.1241
  (0.1129 to 0.1352); 22 of 22; validation 0.1241.
- The control at 4 blocks (no positions, every MLP 4 hidden units wider:
  2064 more weights, against positions' 2048): `3.396 +- 0.01455`; minus
  the model without positions, paired, +0.0036 (-0.0041 to +0.0114): no
  difference; its gap to learned 0.2049 (0.1942 to 0.2157).
The question's answer: positions are worth 0.288 bits at one block and less
at every block added, 0.124 at eight, never 0 by eight blocks; no depth
without positions matches even one block with them (the best without,
8 blocks, 3.384; the worst with, 8 blocks, 3.260; one block with, 3.196):
at this size (width 64, windows of 32) and budget (300 steps), more than
eight blocks.
The predictions (question.py, committed at 01:58:23, before the pilot
at 01:59:24; PREDICTIONS, the constants and judge are unchanged since,
checked by parsing the commit's file; rule_text, the words a table prints,
was reworded): one_block held (0.288); shrinks held (0.288, 0.271, 0.201,
0.141, 0.124); size_one held (0.278 to 0.298); again did not hold (0.201,
against 0.0325 to 0.13); not_closed held (0.113 to 0.135); depth_no_substitute
held (Welch, none at 8 minus learned at 4: 0.183 to 0.202); not_weights
held (the control closes -1.8% of the gap). Six of seven.
Not expected, each seen after the runs (the paper's section 6 says so):
1. The rate, more than the depth: at 4 blocks, seed 0, the gap on
   validation is 0.016 at 0.0015, 0.076 at 0.003, 0.167 at 0.006, 0.169 at
   0.012. From 08.03's 0.003 to the searched rate the model with positions
   gained 0.117 bits on validation, the model without 0.025. 08.03's 0.065
   was a number at one rate for both; with each model's rate searched it
   is 0.201 (3.1 times). At 0.0015 positions are worth almost nothing at
   any depth (0.005, 0.019, 0.016, 0.004, -0.002). Why the model with
   positions needs the larger step is not measured.
2. shrinks held for another reason than it gave: with positions the best
   depth is 2 blocks (3.164); from 2 to 8 blocks it gets worse by 0.096,
   the model without positions better by 0.051; 65% of the gap's fall
   from 2 to 8 is the deeper model with positions doing worse in 300 steps.
3. Pairing bought nothing: paired intervals 0.97 to 1.11 times Welch's; the
   two arms' correlation over seeds -0.17 to +0.15 (13.02's heads: +0.60,
   26% narrower). The spread of the gap is the model with positions'
   (sd 0.019 to 0.035 against 0.004 to 0.018 without).
4. Validation and test agree within 0.007 bits on every gap; test is a
   little harder than validation for these models (by 0.014 to 0.024 bits,
   not the 0.2 07's count models showed).
5. The pilot's spread was not the experiment's: at 8 blocks the pilot (rate
   0.003) measured sd 0.0064, the experiment (rate 0.012) 0.025, which
   asks 15 pairs; the rule that took the largest spread (22) covered it by
   luck. At 2 blocks the experiment's sd 0.035 would ask 26 for a gap of
   0.02; the gaps found are 7 to 14 times that.
The follow-up (the playbook's step for a best at the edge of the range),
recorded in experiments/recorded/followup (depth/..., output.txt):

    python3 -m experiments.depth "depths=[4]" "rates=[0.012,0.024,0.048]" seeds=3 steps=300 every=100 out=experiments/recorded/followup

96 s at load 8 to 10 (02:53 to 02:55; it was run twice, the first time,
97 s at load 9 to 11, printing the verdicts of a one-depth run, which
depth.py now marks "not run here"; the second run's files are byte for
byte the first's, and output.txt is the second's). Validation bits at
0.012, 0.024, 0.048: none 3.379, 3.415, 3.867; learned 3.210, 3.235,
4.045: at 4 blocks 0.012 is the best rate for both, not a limit. Its three
pairs, at the experiment's rates and seeds, are the experiment's seeds 1
to 3 again, the same bytes (cmp of every log.jsonl and summary.json): a
second command, in another folder, made the recorded runs again. The other
depths' edges (2, 6 none, 8) were not followed up.
The recorded runs, the hour: the pilot 157 s, the experiment 2817 s, the
follow-up 96 s: 3070 s, 51 min 10 s, at load 8 to 19. Files: 938 (pilot 49,
depth 849, followup 39, paper 1), 245 KB. No weights.

The default (`python3 -m experiments.depth`): depths 1 and 2, rates 0.003
and 0.006, 2 pairs, 150 steps; then the record. Both models at both depths
choose 0.006; test gaps 0.0999 at one block and 0.0581 at two, neither
interval clear of 0 (t at one degree of freedom, 12.7); its verdicts
(one_block held, shrinks held, size_one not settled, not_closed at two
blocks did not hold, three not run here). 27 s at load 7 to 8; 24 s at load
5 to 6. The Break it (the pairs at 0.003 for both, in main()): gaps
-0.0007 and -0.0077, positions worth nothing at 150 steps, the model with
positions behind on every pair.

### 15.03 The paper, and a repository anyone can rerun

experiments/paper.py writes experiments/recorded/paper/paper.txt (231
lines, 100 columns) from the two records, the follow-up and question.py;
every number is read from a config.json, summary.json or output.txt, or
computed from them (the text's size and SHA-256 from its bytes); others'
numbers and the predictions from question.py. Sections: title, abstract
(four sentences), 1 the problem (08.03's order test as the example), 2 what
the paper shows (each a number with its section), 3 method, 4 results (the
table), 5 the predictions with rules and verdicts, 6 what was not expected
(computed paragraphs: the rate, why the gap shrinks, pairing, validation
against test, the edges, the follow-up), 7 what others found (RELATED), 8
limits, 9 the commands, made from config.json by command(), which keeps a
setting only when its recorded value is not the script's default (read
from the script's source by ast, never imported). 1.6 s. The words that
depend on a number are chosen by it (closes / stays above 0; how many
blocks match; the control's share; the follow-up's choice).
Read against Peyton Jones's slides (see What was read): one ping, the
four-sentence abstract, an example first, refutable contributions with
forward references, related work late and generous, weaknesses said. Not
followed: the active voice everywhere (the generated sentences often state
numbers without a subject), and the intuition is in words in section 1,
with no figure inside the text.
The Break it: depth.py's default warmup 50 made 40; the paper's commands
gain `warmup=50` (both depth.py lines), the recorded value no longer the
default.
The rerun on the page: `python3 -m experiments.depth "depths=[4]"
"rates=[0.012]" seeds=1 steps=300 every=100 out=runs/again` in the
project at 15.03, then cmp against experiments/recorded/depth/
blocks4-learned/seed1/{log.jsonl,summary.json}: the same bytes, 27 s at
load 5.

### Departures from the design, and why

- The design's numbers changed nothing in the claims; the lesson changed
  with the measurement: the gap at 4 blocks is 0.201, not 08.03's 0.065,
  and the module's "result you did not expect" is the learning rate.
- One control row, at 4 blocks (08.03's depth), not at the shallowest:
  where the gap first raised the question. The control model is the
  no-positions model of the seed with each block's MLP made 4 hidden units
  wider (depth.py's Wider, the first units copied), not a model built with
  a wider MLP: models/gpt.py is not this agent's to change.
- The search is a grid of four rates, 0.0015 to 0.012 (factor 2), the same
  for both models at every depth, on seed 0, not 13.01's random draws: in
  one dimension the playbook allows a grid, and the grid holds 08.03's
  0.003. Seven of ten choices fell at its top; the follow-up widened it at
  4 blocks only (the hour). 13.01's aside holds here too: one seed chose
  each rate.
- The pilot was run at depths 1 and 8, 4 pairs, at 08.03's rate, not at the
  rates the search would choose (the search had not run); the number of
  pairs is the largest spread's, by a rule in pilot.py as it ran (decide);
  it asked 22 and 22 ran. The predictions file was committed before the
  pilot; pilot.py and depth.py were committed after the pilot ran (3ae8395,
  02:03:51) and before the experiment's results were read.
- The recorded runs took 51 minutes, inside the hour, on a machine at load
  8 to 19; on a quiet machine about 30 to 35 (the defaults ran 20 to 25%
  faster at load 5 than at 7).
- Every lesson has a test (./learn check reports "lesson has no test"
  otherwise), and every lesson has code: 15.01 question.py's regions
  (pair, trained, judge, budget, read_runs) and pilot.py; 15.02 depth.py's
  search and Wider, question.py's choose and gaps; 15.03 paper.py's
  defaults, command, abstract and verdicts. Labels "with code, decision
  boundary" on all three.
- depth.py with seeds=1 printed a traceback at its table (an interval of
  one pair asks t_quantile for 0 degrees of freedom: a math domain error,
  after every run had written its files). table() now prints one pair's
  bits with "no interval, and no verdict, from one pair" and returns; found
  by 15.03's test, fixed after the recorded runs (printing only: the runs'
  files are the same).

### The lessons, the art, and what the pages measured

lessons/15-your-own-result/: README.md, 15.01 to 15.03 (labels "with code,
decision boundary"), cover.svg and icon.svg (art/outlines/research_art.py's
module 15 cover is now drawn from the recorded experiment: the gap against
blocks with its intervals, 08.03's 0.065, and the path question,
predictions, pilot, experiment, paper, its numbers asserted), and 14
figures from art/research/figs15.py (no training; it reads the records,
question.py and data/fetch.py) besides the three maps (archmap.py: piece
"15" comes with 15.01, the three lessons, MODULE_TITLES; figlib.MODULE_DIRS
"15"). Looked at on the site in both themes (port 8115, shot.py).
- 15.01: the questions the track's results leave, each with the minutes of
  the recorded run it extends (from the records' output.txt: 08.03's pilot
  plan 43, 14.04 27, 10.05 42, 13.04 three budgets 153; TinyStories'
  grammar not on a laptop); what the search found, honestly partial; one
  model, one text, one number, one budget; the predictions; the pilot.
  Found while writing: 10.05's recorded logs have SwiGLU's held-out curve
  ahead of the base from step 100 at width 128, where 10.03 found it behind
  after 150 steps at width 64: "the width or the steps?" is one of the
  page's questions, not run. The page's pilot (3 pairs at 1 and 2 blocks,
  30 to 35 s) asks 27 pairs, against the record's 22. Break it (the weight
  copy taken out of pair): the model with positions' sd at one block 0.0072
  against 0.040 and 7 pairs, not 27; a spike outside the page, 10 seeds of
  each at one block (lr 0.003), gave sd 0.0234 paired and 0.0215 built on
  its own, gaps 0.151 and 0.154: no difference; three seeds' spread is that
  rough. The page says so.
- 15.02: the obvious experiment and its three faults (one rate, three
  seeds, unpaired); the plan; the default (two depths, two rates, two
  pairs, 150 steps) and the record; the results and each surprise; the
  follow-up. Break it: the pairs at 0.003 instead of the searched rate:
  gaps -0.0007 and -0.0077 at 150 steps.
- 15.03: the paper whole in Run it, read against Peyton Jones; a
  repository anyone can rerun, on the track's own project (seven points);
  a checklist for publishing one's own; the rerun session (one depth, one
  rate, one pair of the recorded command: the same bytes, cmp). Break it:
  depth.py's default warmup moved, the paper's commands gain warmup=50.

### Tests (module 15)

`./learn test research 15`: all 3 pass (15.01 39.7 s, 15.02 42.4 s, 15.03
13.7 s, load 5 to 6). Each runs its exact checks first (inside()):
- 15.01: the seven predictions complete, every rule kind judge knows, and
  judge's outcomes on made gaps (largest, falls, above with all three
  answers, clear, about, worse with all three, closes_under); pair: every
  shared tensor equal, positions.weight only in the learned arm, another
  seed other weights; the two arms of a seed draw the same windows (a spy
  on the Run's rng, 3 steps); trained scores the test text only when asked
  and counts the weights; budget against a line worked by hand; read_runs
  against runs lab.Run wrote. The recorded pilot: both arms at 1 and 8
  blocks, 4 seeds, configs equal but the label, no test bits, logs from 0
  to the last step, positions adding context x width weights; the pairs
  its spread asks (seeds_needed, run in the project) equal the pairs every
  recorded depth ran. The default: predictions before the pilot, 3 seeds a
  depth, positions worth more than 0.05 bits at one block on every seed,
  no test bits, a number of pairs, the recorded 22 read back, the budget;
  a tiny run twice, the same bytes.
- 15.02: choose; gaps against lab.difference (paired narrower than Welch's
  on runs made to move together); Wider: the MLP's weights copied, the new
  units drawn as GPT-2's, the same function once their way out is zero;
  widen adds context x width weights within 2% at 1, 2, 4 and 8 blocks;
  search on a tiny text: every rate for both arms, seed 0, validation
  only; results reads the search back. The record: depths 1 to 8, three
  rates or more, 300 steps, the control at 4; every search run seed 0 at
  its rate with validation bits only; every pair at the rate its search
  chose, seeds 1 to n, settings equal but seed, label and rate, logs and
  test bits; the control's seeds, rate and weights; the result (the gap at
  one block over 0.1, every pair positive there, more than twice the
  deepest's, the largest of all depths). The default: 2 pairs at 1 and 2
  blocks, positions over 0.05 bits at one block on both, 14 verdict lines,
  3 "not run here"; a tiny run with the control twice, the same bytes.
- 15.03: defaults reads a CONFIG from a file that would stop if imported;
  command keeps only what differs from the defaults, quotes lists, leaves
  the runner's keys out, and gives back the recorded pilot's own command;
  the paper from a fixture of runs written by the test: its gap and
  interval, the pairs asked, the verdicts, four sentences of abstract,
  every prediction's words. Then the recorded paper: printed as written,
  equal to experiments/recorded/paper/paper.txt, nine sections, seven
  verdicts, the experiment's command with exactly the settings that differ
  from depth.py's defaults, the text's SHA-256; and the command run in a
  clean copy of the project (no runs, no records), cut to one block, the
  rate chosen there and two pairs: blocks1-none and blocks1-learned seeds 1
  and 2, log.jsonl and summary.json, byte for byte the record's.
`./learn check-skeleton research 15` ok (15.01 fails at judge, 15.02 at
choose, 15.03 at defaults); the whole track's ok, 1 min 26 s. `./learn
verify --fresh research 15` ok, 150 s at load 4 to 6 (15.01 65 s, 15.02
52 s, 15.03 33 s). `./learn test research 08` all 5 pass (3 min 52 s) and
`13` all 4 (1 min 55 s), at load 6 to 12: nothing of theirs changed.
`./learn selftest` ok (269 tests). `./learn check-timeline research` ok,
8 min 24 s at load 6 to 12: the project has 507 files at 15.01, 1396 at
15.02 (the recorded experiment and follow-up) and 1398 at 15.03. `./learn
check`: nothing for research 15 (the lines left are research/13.0N
without their lessons yet, and another track's).

### For the harness, and what a page writer meets

- No harness change. track.py's module-15 part is the last block of the
  file: the three experiments in EXPERIMENTS (short settings for the
  timeline), DATASET_OF (none), pilot.py placed at 15.01 by FILES_FROM,
  and the four recorded folders (pilot 15.01, depth and followup 15.02,
  paper 15.03) first in FILES_FROM with DATA lines.
- The recorded experiment is 849 files (282 runs, three files each, and
  its figures and output). The Code of 15.02 shows every one as a data
  block, as 14.04's 55: the harness quirk plans/research.md lists (one
  collapsed block for a DATA glob) makes that page very long until it is
  fixed. Not worked around: the runs keep 00.02's one folder a seed.
- Lead-in names: question.py, depth.py and paper.py define results, texts,
  table, search, choose, gaps, widen, paper, seconds, blocks, gather, para,
  took, surprises; a "###" heading that holds one of these words is pulled
  into The code. The pages' headings avoid them ("The shape it takes",
  not "The shape of the paper").
- 15.03's Run it is the whole paper (234 lines): the reading needs it.

### Checked, and not checked

Checked: every quote of Hamming, Schulman, Peyton Jones's slides, the
playbook and the five papers found again in their text; the predictions,
SMALLEST, LEVEL, POWER and judge unchanged since the commit before the
pilot; the pairs share every weight but the table, and draw the same
windows; the follow-up's pairs and the page's rerun are the record's bytes;
the paper's numbers against the record (the cover asserts the gaps); the
defaults' times on a machine at load 5 to 6 (pilot 30 s, depth 24 s, paper
1.6 s). Not checked: other widths, windows or budgets (the gap may well
depend on the steps: the model with positions is best at 2 blocks after 300
steps, and deeper ones are not trained as far); the edges of the search at
2, 6 and 8 blocks; whether the spread of the gap would shrink with a search
on several seeds; why the model with positions wants the larger rate; a
token marking each window's start (Kazemnejad et al.'s proof uses one);
Linux. The published work beyond the five papers read, which were found by
a few searches: someone may have measured this.
