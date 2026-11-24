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
engine/nn/functional.py 02.04   relu tanh log_softmax softmax cross_entropy;  05.02 dropout
engine/nn/init.py       04.02   calculate_gain normal_ uniform_ zeros_ ones_ xavier_* kaiming_*
engine/optim/__init__.py 03.01  Optimizer, SGD;  03.02 momentum (dampening, nesterov);  03.03 Adam;  03.04 AdamW
engine/optim/lr_scheduler.py 03.05  LambdaLR
lab/run.py              00.02   config() (key=value settings), Run (config.json, log.jsonl, summary.json, rng)
lab/stats.py            00.03   mean sd spread welch_t
lab/plot.py             00.03   ticks, lines(): SVG line plots of plain elements, text in currentColor
lab/safetensors.py      02.05   save_file, load_file, read_header (numpy arrays; the library's numpy API)
lab/schedule.py         03.05   warmup_cosine
lab/checks.py           04.06   the five checks
data/points.py          01.04   two_groups: two moons from a seed
data/fetch.py           03.01   the explicit download, pinned sizes and SHA-256 (whole, no regions)
data/mnist.py           03.01   read_idx, load(split, n, standardise)
data/__init__.py        03.01   batches(n, size, rng)
data/augment.py         05.03   shift(x, k, rng, fill)
experiments/<name>.py   one per lesson (below); loop.py (03.01) and deep.py (04.01) are shared code
tests/                  NNLL_*.py one per lesson; support.py, helpers for the PyTorch comparisons
```

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

## For the harness work and module 06

- verify_tools() names python3 and numpy only. MNIST is a download, not a
  program, so `needs=` cannot see it; the plan's `./learn fetch` and a
  "missing" for downloads are still to do (data/fetch.py is what it should
  call).
- `models/` does not exist yet: 00 to 05 build their small networks inside
  each experiment (deep.py and loop.py take the engine as an argument).
  06.02's "one import" is already true of every engine-era script here.
- `experiments/` is the plan's `papers/<name>/`: one file per lesson, since
  most of 00 to 05 are not papers.
