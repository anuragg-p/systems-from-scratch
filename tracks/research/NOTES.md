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
lab/schedule.py         03.05   warmup_cosine
lab/checks.py           04.06   the five checks
lab/devices.py          06.02   device(torch, name), clock(torch, dev): where a PyTorch run computes, and its time
data/points.py          01.04   two_groups: two moons from a seed
data/fetch.py           03.01   the explicit download, pinned sizes and SHA-256 (whole, no regions)
                        06.03   cifar10: one archive, resumed if dropped, unpacked, every file pinned (@from blocks)
data/mnist.py           03.01   read_idx, load(split, n, standardise)
data/cifar.py           06.03   read_records, load(split, n): CIFAR-10's binary records, standardised per channel
data/__init__.py        03.01   batches(n, size, rng)
data/augment.py         05.03   shift(x, k, rng, fill);  06.03 crop_flip(x, pad, rng)
data/tinyshakespeare.txt 07.01  the text, shipped byte for byte (no regions; FILES_FROM and DATA in track.py)
data/shakespeare.py     07.01   load, chars, encode, decode, split(name): the text as numpy character numbers
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
experiments/<name>.py   one per lesson (below); loop.py (03.01) and deep.py (04.01) are shared code
                        06.03   images.py: the PyTorch-era loop, tensors(dev, ...), train_epoch, evaluate
                        07.02   sequences.py: bits, contexts, context_bits, sample;  07.03 windows, window_bits
                        08.01   language.py: train, the loop module 08 shares;  08.02 attention_maps, looks
                        08.04   language.py: held_bits (and train's held), save, load;  08.05 top_k, top_p, generate
experiments/recorded/   06.04   the long run of resnet.py, recorded (DATA in track.py; see "Long runs")
                        07.02   recorded/nplm/: the long run of nplm.py
                        08.04   recorded/gpt/: the long run of gpt.py (no weights: model.safetensors is not shipped)
tests/                  NNLL_*.py one per lesson; support.py, helpers for the PyTorch comparisons
                        08.02   support.py: gpt_numpy and its pieces, the GPT again in float64 numpy
```

From 06.02 the project needs PyTorch too (`pip install torch`; the CPU build
is enough), and from 06.03 CIFAR-10 (`python3 -m data.fetch cifar10`).
Module 07's text, Tiny Shakespeare, ships with the project: nothing to fetch.

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
