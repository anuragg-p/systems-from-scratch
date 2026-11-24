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
experiments/<name>.py   one per lesson (below); loop.py (03.01) and deep.py (04.01) are shared code
                        06.03   images.py: the PyTorch-era loop, tensors(dev, ...), train_epoch, evaluate
                        07.02   sequences.py: bits, contexts, context_bits, sample;  07.03 windows, window_bits
experiments/recorded/   06.04   the long run of resnet.py, recorded (DATA in track.py; see "Long runs")
                        07.02   recorded/nplm/: the long run of nplm.py
tests/                  NNLL_*.py one per lesson; support.py, helpers for the PyTorch comparisons
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
after an unseen context (2.513 against 2.416 at 5). Times: steps take 1.2
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
  seed, 2.369).
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
- The models/ docstring (06.02) says every model after convnet imports
  torch; models/ngram.py (07.02) is numpy only. Left as it is: the file
  comes with 06.02, and a note about 07.02 there would be a later lesson's
  text in an earlier file.

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
