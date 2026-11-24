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
models/__init__.py      06.02   (no regions) the networks experiments share, one file each
models/convnet.py       06.02   convnet(torch, width): 3 convolutions and a Linear layer, on either library
models/resnet.py        06.04   Block, ResNet; resnet(n, residual, width), layers(model): He et al.'s CIFAR network
experiments/<name>.py   one per lesson (below); loop.py (03.01) and deep.py (04.01) are shared code
                        06.03   images.py: the PyTorch-era loop, tensors(dev, ...), train_epoch, evaluate
experiments/recorded/   06.04   the long run of resnet.py, recorded (DATA in track.py; see "Long runs")
tests/                  NNLL_*.py one per lesson; support.py, helpers for the PyTorch comparisons
```

From 06.02 the project needs PyTorch too (`pip install torch`; the CPU build
is enough), and from 06.03 CIFAR-10 (`python3 -m data.fetch cifar10`).

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

06.01 to 06.04 were timed twice, the second time with other agents' runs
going (load average 6 to 8): conv 26.4 and 27.0, switch 3.7 and 4.1, cifar
42.1 and 43.4, resnet about 50 and 53.5. Same digits both times.

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
error after it 86.4 against 89.0 on average) and stay apart; the residual
56 is below the residual 20 from pass 1 on (82.3 against 82.9, then 65.0
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
