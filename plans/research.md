# Plan: track `research` - AI research, from a first experiment to your own result

Status: building, taken up again on 2026-11-24 (direction set by Fable;
implementation by Opus agents). The outline is plans/research-outline.md
(moved out of outlines/ when tracks/research took the id over): its
modules and lesson titles are the list to build. Its module art stays in
outlines/ai-research/ until every module has copied its cover and icon.
This file holds the decisions.

## Where it stands (2026-11-25)

On master: modules 00 to 05, code, tests and all 27 lessons. The clean-up
is finished and merged: `./learn verify --fresh research` passes 27 of
27 (8 min 27 s), with the tests, check-skeleton, check-timeline and
check; a read across the modules fixed eleven cross-references, terms
used before their lesson and numbers that disagreed with NOTES.md. The
covers of 00 to 04 and 15 and the track card are redrawn from the built
track's own numbers; the generator, art/outlines/research_art.py, writes
each built module's cover to both outlines/ai-research/NN/ and
tracks/research/lessons/NN-*/ and stops if a lesson's number changes.

Left by the read, on purpose: "spread" is used for the lab's one-line
result, for the spread over a batch, and as a plain word for a standard
deviation; 05.03 calls MNIST's background "white"; a few facts about
the papers (the Adam paper's 200 passes, 05.04's credit to Belkin) are
not checked against the sources.

The core is on master whole: modules 00 to 15, 70 lessons, each with
its code, its test (70 of 70 pass, 2026-11-25), its page, figures and
map, and each module with its page, cover and icon; twelve recorded
runs, no weights. Every module's `./learn verify --fresh` passed on its
lessons' branch (08: 534 s; 09: 315 s; 10: 524 s; 11: about 750 s; 12:
342 s; 13: 274 s; 14: 201 s; 15: 150 s); `./learn check` has nothing
for research. Pushed on 2026-11-25 up to module 15; module 11 after it
is local. 08.02's default run is 2 seeds (3 took 82 s on a loaded
machine); its heads comparison is inside the noise at 2 seeds and the
page runs that part at 3 as well (13.02 settles it at 10). 10.02's
reason for its slower step was wrong and is corrected from 11.02's
measurement.

`./learn verify --fresh research` on master, the whole track at once:
ok, 70 of 70 lessons, 4348 s (2026-11-25, at a load of 9 to 15).

The default runs seen nearest a minute, timed again on master at a load
of 9 to 11: 08.02 34 s, 09.03 35 s, 12.01 46 s, 12.03 35 s, 13.02 34 s,
all well inside. 11.05 took 66 s and then 49 s at the same load (58 s
at a load of 6 when it was built): the one default still to be timed
with nothing else running, and cut if it passes 55 s then.

In work, two agents: a read of modules 06 to 10 and of 11 to 15 for
terms, cross-references and promises between lessons that were written
out of order, as was done for 00 to 05. Left after that: 11.05's time
on a quiet machine; the README's map (`./learn map --write`) when the
other session's README changes are in. The shelf (16 to 21) is not
started.

The owner asked for more speed (2026-11-24): the limit of three agents
is lifted. Timings taken while four or five agents run are not to be
trusted, so a default run is no longer cut for time by an agent; one
pass on a quiet machine at the end measures every default run again
and fixes what is over a minute and the times the pages state. Module
11 (fast) is all timings: its code is built when nothing else is
training.

After that, as agents finish: each module's lessons after its code;
11's code after 10's (both change models/gpt.py); 15 after 13's code
(it uses 13's tools), its worked example a question the track's own
results raise (the plan's candidates, or 08.03's: how much of what
learned positions are worth is left as blocks are added).

Still open, not in work:
- The worst of the harness quirks below: a recorded run is shown in The
  code as one block for each file, 13 on 14.03 and 55 on 14.04, whose
  page is about 50,000 px tall. It needs one collapsed block for a
  DATA glob, in harness/.
- Harness quirks the writers met, for whoever next works in harness/: a
  `###` heading in How it works that contains a definition's name is
  pulled into The code; lead-in names match case-insensitively; brackets
  in a figure caption break the image line; `conv2d` and `Conv2d` are
  one lead-in name; a lead-in for a function inside an `@from` block
  does not attach. A `DATA` glob is shown as one block per file: 06.04's
  recorded run is 41 blocks in The code, where one folded row would do.
  Figures use only the theme's colours, so 06.03's photographs come out
  as negatives in the dark theme. harness/ and README.md have
  another session's uncommitted changes in the main checkout: agents do
  not edit them, and README's map (`./learn map --write`) is regenerated
  only when that is clear.

Decided on 2026-11-24 (Fable):
- Devices: every PyTorch-era experiment has a `device` setting whose
  default is `cpu`, so a page's numbers and times are CPU numbers and
  verify replays them; `device=auto` takes cuda, then mps, when present.
  This narrows "used when present" below: present and asked for.
- CIFAR-10 is fetched in its binary form (records of bytes), so the
  learner's reader parses bytes and nothing is unpickled.
- The engine gains convolution in 06.01 and nothing after it.
- Threads: nothing sets a thread count, from 06.02 on. The same seed on
  the same machine at its default gives the same digits; another thread
  count can change the last ones (07's small layers do), which is the
  "across machines" case the pages already allow for.
- A module's one long run goes to the paper's claim that needs it. A
  lesson whose short run falls short says so, with the settings of a
  longer run the reader can make and its measured time.

Decided by the owner, 2026-11-14:
- One track, a core and a shelf: the core runs from a first gradient to a
  result of the learner's own; optional modules after it each take one
  field's founding papers. The shelf can grow without touching the core.
- Own engine first, then PyTorch: the learner writes autograd and tensors
  in numpy under PyTorch's names, proves them against PyTorch, and from
  the first model that needs scale runs the same scripts on PyTorch.
- Laptop only: nothing in the track needs a rented GPU.
- "Plan with Fable, execute with Opus."

## What the learner ends with

An engine they wrote that gives PyTorch's gradients; a GPT that loads the
published GPT-2 weights and gives the reference's logits; the central
idea of more than twenty papers written into their own code and tested;
one published figure reproduced (grokking); one small result of their
own, written up, with a repository anyone can rerun.

## The shape of every lesson that has a paper

Train the obvious thing. Watch it fail: it does not learn, learns too
slowly, forgets, or memorises. Bring in the paper's idea as a change to
code the learner already has. Run the paper's own experiment at laptop
size. Say what held and what did not. A lesson that opens with the paper
and then looks for a use is wrong (the same rule as dsa's tools).

## Decisions

- Language: Python 3, numpy. PyTorch from lesson 06.02 on (the CPU build
  is enough; an Apple or CUDA GPU is used when present, never needed).
  The learner's code imports nothing else: no torchvision, transformers,
  datasets, tiktoken or matplotlib. Internal tests may use tiktoken and
  transformers as the reference, the way db's tests use sqlite3.
- The engine (modules 01 to 05) implements only what the lessons use,
  under PyTorch's names and argument order. A script names its engine in
  one line (`import engine as torch`, later `import torch`); a test runs
  every engine-era script on both and compares.
- Held to the real thing, four ways: gradients against PyTorch (1e-6, in
  float64); token ids against tiktoken; logits against the reference
  implementation on the published weights (GPT-2 small, then one current
  open model); and each paper's claim against our own run.
- Time: every "Run it" finishes in under 60 seconds on a laptop CPU. A
  long run is marked on the page with its measured CPU time, at most one
  per module and at most 60 minutes; it ships with its recorded config,
  log and curve, and the page's own Run it is a short version of it that
  `./learn verify` replays.
- Numbers: same seed, same machine, same digits (00.02 shows it; a test
  holds it). Across machines the last digits can differ, so pages print
  three or four significant digits, verify uses `vary` only where a
  number really differs, and tests assert tolerances and thresholds over
  fixed seeds, never exact floats.
- Every reported result is several seeds, from module 00 on. One run is
  never called a result.
- Paper rule: a lesson that implements a paper names it, states the one
  claim it tests in the paper's own terms (its figure or table), runs
  that experiment at laptop size, shows our number beside the paper's and
  says what held. We never print a number we did not run and never call a
  laptop-size run a reproduction of the full-size result. Paper figures
  are never copied: ours are drawn from our runs.
- Theory rule: code first, theory second, as everywhere on the site. A
  lesson with a formula derives it once on the page in plain steps, and a
  run checks it in numbers (the nudge from 01.01, or PyTorch), held by a
  `fact` annotation. Maths arrives where it is first needed (the chain
  rule in 01, matrices in 02, logarithms and probability in 02.04 and
  07.01); there is no maths module.
- Curves: the runner draws its own SVG line plots from a run's log, so a
  lesson's curve figure comes from a real run, as stepped figures do.
- Data and weights: small inputs ship with the track (Tiny Shakespeare,
  generated points, modular arithmetic). The rest is fetched once, by an
  explicit command, with pinned checksums, into a cache outside the
  project: MNIST (first used 03.01), CIFAR-10 (06.03), GPT-2 small
  (09.03), a TinyStories subset (09.04), one current open model (10.04),
  CLIP (19.04). No build, test or lesson downloads on its own; a missing
  download is "missing" to verify, as a missing QEMU is. This departs
  from dsa's "never downloaded", for size. Each licence is read, not
  assumed, and recorded in NOTICE.
- Terms as read at the source on 2026-11-14 (none of these is
  redistributed; the learner fetches each):
  - MNIST, 11.6 MB: the original page states no licence and no longer
    serves the files (Keras says CC BY-SA 3.0, Hugging Face says MIT).
    Fetched from the mirror torchvision uses.
  - CIFAR-10, 170 MB: no licence; the page asks only that the tech
    report is cited.
  - Tiny Shakespeare, 1.1 MB, from karpathy/char-rnn: public-domain
    text. The one input small and free enough to ship.
  - TinyStories: CDLA-Sharing-1.0; the training file is 1.9 GB, so the
    track fetches a subset.
  - GPT-2 small: `model.safetensors`, 548 MB; the model card says MIT,
    the repo Modified MIT.
  - SmolLM2-135M: Apache-2.0, 269 MB, confirmed to use RMSNorm, rotary
    positions, a SwiGLU MLP and grouped-query attention (9 heads on 3
    key/value heads).
  - CLIP ViT-B/32: 354 MB; the code is MIT, the weights have no licence
    of their own, and the model card puts any deployed use out of scope.
    Loading it in a lesson is research use; say so on the page.
- Layout: `engine/` (the learner's library), `lab/` (the runner: config,
  seed, log, plot), `data/`, `experiments/<name>.py` (one script per
  lesson; a recorded long run sits beside its script) and, from module
  06, `models/` (resnet, gpt). One file per lesson, so agents in
  parallel never edit the same file.
- Tests are internal, three kinds: differential (engine against PyTorch,
  tokenizer against tiktoken, logits against the reference); learning
  (each experiment's short run reaches a threshold on fixed seeds, and
  fails with the lesson's code cut out); reproduction (the shape of each
  recorded long run, rerun only on demand).
- Scripts, not notebooks. No cloud, no distributed training, no serving
  (the inference track), no prompt engineering or API calls.
- Art is not optional: track card and icon, cover and icon per module,
  the architecture map and at least one diagram in every lesson.

## The paper map (core)

Lesson, paper, and the claim we run again at laptop size. Modules 00 to
05 are built: what held is stated as found (numbers in
tracks/research/NOTES.md). The rest is still the plan.

Built, as found:
- 03.03 Adam: on MNIST the paper's comparison is a tie at laptop size
  (logistic regression, as the paper's own figure shows; the multilayer
  network, nothing beyond noise). The lesson's failure-then-fix is
  therefore Adam's stated property, not the race: rescale the gradient
  and plain descent needs a new rate while Adam takes the same steps.
- 03.04 AdamW: with SGD an L2 term and weight decay are the same step;
  with Adam they are not, and weights that get no gradient show it
  exactly. The paper's "wider good region" did not show at this size.
- 03.05 Cosine decay and warmup: both held.
- 04.02 Glorot, He: held at the paper's 30 layers.
- 04.03 Batch normalisation: reaches 90% in half the steps on the
  paper's own network, and trains at a rate that diverges without it.
  It is not faster at a rate that already works.
- 04.05 Residual: the deeper plain network trains far worse (held).
  With shortcuts the deeper one trains about as well, not better.
- 05.01 Rethinking generalisation: fits random labels (held).
- 05.02 Dropout: lower test error (held, on 2000 images).
- 05.04 Double descent: held strongly, on the random-features model the
  paper cites, not on a network trained by gradient descent.

- 06.01 Convolution: the network with a ninth of the weights is better
  and loses less when digits move, but is far from shift-proof: the
  convolutions move their features with the digit exactly, and the last
  layer reads each place with its own weights.
- 06.02 The switch: on this laptop's CPU PyTorch is only about twice as
  fast as the engine. The case for it is the GPU and what the next
  lessons need, not speed on a CPU.
- 06.04 ResNet on CIFAR-10 (He et al., figure 6), the recorded run: 20
  against 56 layers, 4000 images, 8 passes, 3 seeds, 40 minutes of CPU,
  at a tenth of the paper's rate (at the paper's 0.1 the deeper
  residual network does not get going in so few steps; the paper warms
  its 110 layers up at 0.01 too). Plain: 56 layers train worse than 20
  (held). Residual: 56 train better than 20 (held). The page's short
  run, 8 against 20 layers, shows only the plain half beyond noise.

- 07.01 Shannon (1951): folded to his 27 symbols, the text's entropies
  are 4.75, 4.09 and 3.32 bits against his 4.76, 4.03 and 3.32.
- 07.02 Bengio et al. (2003): in the one-minute run the network is far
  ahead of add-k counting but 0.058 bits behind the paper's own
  baseline, deleted interpolation. In the recorded run (3 seeds, 20
  minutes) every seed beats it at 3, 5 and 8 characters (2.346 against
  2.416 at 5). Held, with the longer run; 8 characters no better than 5.
- 07.03 The recurrent network is behind 07.02 at the page's budget
  (2.540). It ignores what is more than 16 characters back; recall is
  right after 10 blanks and at chance after 40; the gradient vanishes
  even in the trained network, through tanh's flat ends.
- 07.04 Bahdanau et al. (2015), figure 2: without attention copying
  falls from 1.00 at length 2 to 0.16 at 20; with it 0.94 or better to
  20, and 0.87, 0.80, 0.60 at 25, 30 and 40, beyond any length trained
  on. Held, with a one-way encoder and greedy decoding.

- 08.01 Without the mask and without positions (08.03's) the model
  cannot find the next character to copy: its reported loss is only a
  little lower (3.26 against 3.57 bits) and, asked from the past only,
  it is far worse (4.20) and writes one character over and over. The
  planned "falls to nothing" needs positions. Without the division by
  sqrt(d): 3.752 against 3.581.
- 08.02 Attention stacked four deep without the rest of the block is
  worse than one layer (4.60 against 3.73); four blocks beat one (3.41
  against 3.50); four heads against one at equal weights, 3.407 against
  3.433, barely beyond noise.
- 08.03 The order test is exact for one block only (3.6e-15). From the
  second block on the causal mask lets order in (the scores move by
  2.44), as Haviv et al. (2022) found at scale. Learned positions still
  help: 3.342 against 3.407.
- 08.04 The recorded run (6 blocks, width 192, 2800 steps, 56 minutes,
  2 seeds): without dropout validation turns up near step 1900, test
  2.361; with dropout 0.2 it is still falling, test 2.226, below module
  07's best (2.283) on both seeds.
- 08.05 Holtzman et al. (2020): greedy loops, as they found. At
  character level the rest did not hold: plain sampling is the closest
  to the text's perplexity, the nucleus further off, and with the long
  run's model even plain sampling writes text the model finds likelier
  than the real text.

- 09.01 Sennrich et al. (2016): 15.9% of the test text's different
  words are not in training (6.9% of its running words). BPE at 2048
  gives 2.92 bytes a token on training text, 2.58 held out. The same
  GPT for the same steps: 3.332 bits per character on characters, 2.691
  on BPE tokens.
- 09.02 The same ids as tiktoken and transformers on everything tried,
  but for letters newer than Python's Unicode tables (15.0 here, 16.0
  in tiktoken) before a contraction: 5,004 code points.
- 09.03 Logits identical to transformers' (eager attention). GPT-2
  scores 1.851 bits per character on Shakespeare's test text, never
  trained on it, against 2.226. Holtzman et al. on their own model's
  small sibling, in a 32-minute run that is not recorded: greedy loops
  and pure sampling is above the text's perplexity (held); the nucleus
  is not the closest to the text (did not hold).
- 09.04 Eldan and Li (2023): 4.27 million weights, 45 minutes, 2 seeds:
  0.7367 bits per byte on held-out stories (GPT-2 small: 0.836); 16 of
  16 stories end on their own, none loop, and they share no longer runs
  with the training text than held-out stories do. Whole stories: held.
  Consistent, nearly perfect grammar: did not. GPT-4's grading: not run.

- 14 Power et al. (2022), x/y mod 97, the text's set-up (AdamW, weight
  decay 1). With models/gpt.py's GPT at the paper's 50% of the
  equations there is no delay at all: it generalises as it memorises.
  At 35% the figure appears, 3 seeds: training passes 99% near step
  400 with validation at chance, validation passes 99% 5.0 to 5.6
  times later; the paper's figure 1 has about a thousand times (did not
  hold). What decides it is the start: at 50%, weights started 10 times
  larger give a delay of 4 to 8 times. Without weight decay no seed
  generalises in 6000 steps (held); less data is steeply slower (held);
  the validation loss rises in between, 1.16 times a guess's against
  the paper's about 9 (direction only).

- 10.01 Zhang and Sennrich (2019): RMSNorm 3.561 against layer norm's
  3.563 bits (comparable: held). Its saving in time did not hold on
  this CPU: a step is 11 to 18% slower, because nn.LayerNorm is one
  fused kernel; written out the same way, RMSNorm takes 0.7 of the time.
- 10.02 Su et al. (2021): the score depends on the offset only (3.8e-13
  in float64). 3.248 against learned positions' 3.563 at 150 steps.
  Longer windows run but get worse: 3.265, 3.30 at twice the trained
  length, 3.56 at four times.
- 10.03 Shazeer (2020): SwiGLU at equal weights is behind at 150 steps
  (+0.033) and ahead once trained a while (-0.067 in the long run).
- 10.04 Ainslie et al. (2023): half the key and value heads cost +0.001
  bits. SmolLM2-135M's logits and ids equal transformers'; 1.405 bits
  per character on Shakespeare's test text (GPT-2: 1.851), a text it
  may have been trained on.
- 10.05 The recorded table (4 blocks of 128, 2000 steps, 3 seeds, 42
  minutes): base 2.337; RMSNorm +0.013 and grouped-query +0.009 (not
  beyond noise); rotary -0.060; SwiGLU -0.067; all four -0.089.

- 13.01 03.03's pair again. Adam tuned against SGD at a documented
  default: 6.25% against 14.6% test error. The same search of 8 rates
  for both: 6.25 against 7.06, t = +2.7, a tie by the rule written down
  first. Henderson et al. and the tuning playbook: held.
- 13.02 08.02's heads, decided: at 10 seeds a side four heads are
  better by 0.025 bits (t = -5.7, lower on 10 of 10). The comparison
  was paired all along (one seed gives both arms the same start and
  batches): at 3 seeds Welch's interval does not decide and the paired
  one does. The test text's own sampling error for one model, 0.0138
  bits, is as large as the spread over seeds; for a difference on the
  same text it is 0.0018.
- 13.03 The best of 32 runs chosen on one half of MNIST's test set
  looks 1.11 points better than the average there and 0.78 on the
  other half. CIFAR-10 has 346 test images (3.5%) with a twin in
  training; MNIST and CIFAR-10 have no exact copies; 100 held-out
  TinyStories are word for word in our training stories.
- 13.04 Kaplan et al. (2020): five widths fitted, exponent 0.0971
  counting weights their way; width 256 predicted at 3.904 bits per
  token (3.836 to 3.973) before it was trained, 3.925 trained. Counting
  the embeddings too, the prediction misses by 3.2%. Their exponent,
  0.076, is for models trained to convergence; ours are not.

- 12.01 Radford et al. (2018) on Banking77 (77 classes): GPT-2 with
  every weight fine-tuned 0.900 against the same model from nothing
  0.793 (held). Not in the paper: the frozen body with a new head,
  0.863, loses to a tuned bag of words, 0.882; and a head learns almost
  nothing from GPT-2's vectors until each number is standardised (0.19
  against 0.77).
- 12.02 Hu et al. (2021), the recorded run (3 seeds, 600 steps, 63
  minutes at a load of 9 to 25): LoRA at rank 1, 4 and 8 reaches 0.886
  to 0.889 with under 0.3% of the weights, 1.1 to 1.4 points behind
  every weight's 0.900, beyond noise. Within about a point, rank 1 as
  good as rank 8, a third of the memory: held. "On par or better": did
  not hold at 600 steps.
- 12.03 Five tasks made by code. GPT-2 answers none; after 80 LoRA
  steps 0.375 on new instances, 0.342 in a wording not trained, 0.108
  on a task not trained.
- 12.04 Whether LoRA forgets less depends on the text: on held-out
  TinyStories it does, on Shakespeare it does not. LoRA moved the
  weights further than full fine-tuning, so the distance moved does
  not predict what is forgotten.

- 15 The track's own question, from 08.03: what learned positions are
  worth as blocks are added. 22 paired seeds a depth, each model at the
  rate its own search chose: 0.288 bits at 1 block, 0.271 at 2, 0.201
  at 4, 0.141 at 6, 0.124 at 8, positions ahead on every pair. No depth
  without positions reaches one block with them. Six of seven
  predictions held. Not expected: the learning rate matters more than
  the depth (at 4 blocks the gap is 0.076 at 08.03's rate and 0.167 at
  the searched one), most of the gap's fall is the model with positions
  getting worse with depth at 300 steps, and pairing bought nothing.
  Earlier work (Irie et al. 2019, Haviv et al. 2022, Kazemnejad et al.
  2023) answers part of it; the lesson says so.

- 11 Fast, on 10.05's "all four" GPT. 11.02: the profile corrects
  module 10's guess: rotary's angles are 0.5% of a step, the turning
  itself 15.8%; keeping the angles gives the same weights bit for bit
  and saves nothing. 11.03: PyTorch's fused attention, the same numbers
  (2.7e-15), a step 1.29 to 1.42 times faster on this CPU; nothing on
  the Apple GPU. 11.04: every fact of Micikevicius et al. about sixteen
  bits held on this model's numbers; the speed did not: this build has
  no fast 16-bit product on the CPU and a step is 8 to 29 times slower.
  11.05: accumulation gives the large batch's gradient exactly and no
  speed; time to a target barely moves with the batch. 11.06: a cache
  of keys and values writes the same tokens 2.8 to 6.3 times faster on
  SmolLM2. The recorded benchmark, time to 2.4 bits: fused attention
  x0.87, twice the batch and rate x1.12 (slower), all together x0.86.

Still the plan:

## Decisions after module 08's code (Fable, 2026-11-24)

- The 08.04 long run stays at 2 seeds for each dropout (3 would pass
  the 60-minute limit). The lesson says 2, and claims only what both
  seeds show.
- 08.01 stays as measured. 08.03 does not add a model to show the
  unmasked copy once positions exist; it may leave that as something
  for the reader to try, with no number claimed.
- 08.02's default run (45 to 47 s on a loaded machine) stays unless
  the lessons agent sees it pass 55 s when verifying; then it is cut
  and its numbers and test move together.
- 08.05 scores on the test text, as every lesson does.
- Module 09's tests take their reference from `transformers` (already
  installed, 4.57.6): its GPT-2 tokenizer built from the fetched files,
  its model for logits. Nothing new is installed for a test.

## Decisions after module 09's code (Fable, 2026-11-24)

- Module 09's tests fail with "missing:" and the fetch command when a
  download is absent, as module 06's do. A pass that never compared the
  ids or the logits would say more than it checked.
- 09.03's 32-minute sampling run is quoted on the page as a table, with
  its command and time and the words that it is not recorded, as 08.05
  quotes its checkpoint's numbers.
- 09.02 says that where its ids part from tiktoken's depends on the
  learner's Python (its Unicode tables), and how to see which.
- A default run is cut for time only when it passes 55 s at a load
  average under 6. (08.02 was cut at a load of 10 to 13; it stays cut.)
- tiktoken was installed for the tests (pip install --user). The tests
  use it when it imports and transformers' tokenizers either way.

## Decisions after module 14's code (Fable, 2026-11-24)

- The central figure stays at 35% of the equations with the GPT as
  module 08 built it: one change from the paper's text, and one the
  paper itself varies. The start is the ablation that explains why 50%
  shows nothing here; it is the module's lesson about reproduction (a
  detail the paper's text does not give decides the result).
- 14.04's default run trains nothing and reads the recorded runs; the
  page says so.
- 14.02's default stays at 350 steps (training accuracy 0.96, not yet
  99%): the recorded seeds pass 99% between steps 354 and 446, so 400
  would not show it for every seed either.

## Decisions after module 10's code (Fable, 2026-11-25)

- Rotary's angles are made again on every call (18 to 52% of a step).
  Left as it is in module 10, whose page says the step is slower and
  why; module 11 finds it by profiling and fixes it, its first "the
  same numbers, sooner".
- 10.04 does not say SmolLM2 never saw Shakespeare.
- RMSNorm's speed claim is reported as not holding here, with the
  reason measured.
- Module 11: 11.02's profile leads to Rotary; 11.03 is PyTorch's fused
  attention in place of self_attend; 11.06's one more optimisation is a
  cache of keys and values for writing text, which 10.04's grouped
  heads halve. Its recorded benchmark is taken only on a quiet machine.

## Decisions after module 13's code (Fable, 2026-11-25)

- 13.04's recorded run (51 minutes at a load of 10 to 21) and 13.02's
  (3 minutes) stand: 54 minutes of the hour.
- errorbars' default stays at 3 seeds; the quiet pass measures it.
- 13.01's page gives the aside as found (a search of 16 trials on one
  seed picks a rate that is unstable on fresh seeds) and names the
  remedy, the best trials run again on several seeds before choosing,
  as something to do, with no number: it was not built.
- Module 15's worked example is the question 08.03 raised: from the
  second block on the causal mask lets order in, so how much are
  learned positions worth as blocks are added, and how many blocks
  does a GPT without them need to match one with them? Done with
  module 13's tools: the prediction written down first, the same
  search for both arms, paired seeds, the number of seeds from the
  spread, chosen on validation and reported on test. One agent builds
  the experiment, its recorded run, the paper made from the logs, and
  the three lessons.

## Decisions after module 12's code (Fable, 2026-11-25)

- The recorded run stands at 63 minutes: it was taken at a load of 9 to
  25 and is estimated at 44 on a quiet machine. The page gives the time
  with the load.
- "LoRA did not match full fine-tuning at 600 steps" is the finding. No
  longer run.
- No default run is cut; the quiet pass measures classify and instruct.

## Decisions after module 15 (Fable, 2026-11-25)

- Module 15's records stay packed (one line of runs.jsonl for a run's
  three files, `question.pack`, `unpack` writes them back byte for
  byte): unpacked, 15.02's page was 849 blocks. The same packing would
  shorten the pages of 10.05, 12.02, 13.02, 13.04 and 14.04 (49 to 63
  blocks each) without a harness change; it means changing each
  module's reader and test and verifying its lessons again. Not done;
  for the owner to choose between that and the harness fix.
- The next question the experiment points at (does the gap depend on
  the step budget) is left in the lesson as the reader's.
- 15.03 links Peyton Jones's own page.

## Decisions after module 11's code (Fable, 2026-11-25)

- 11.02 stays as found: the fix the profile was expected to point at
  does not pay, and the profile points at attention instead (11.03).
  torch.compile is not taken (it needs a C++ compiler and moves the
  last bits); it and AdamW's fused step are named in 11.06 as things
  to try, with the spike's ranges given as a trial outside the page.
- 10.02's pages gave the wrong reason for the slower step (the angles
  made again on every call). The module 11 lessons agent corrects
  them from 11.02's measurement.
- The recorded benchmark stands as taken. Three of its rows ran at a
  load of 2 to 11; four rows taken again back to back by the planner
  at a load of 6 to 10 gave the same ratios within a few percent
  (NOTES.md).
- 11.05's default (58 s at a load of 6) is decided in the quiet pass.
- check-timeline's fixed 20 s for one step fails earlier lessons at a
  load of 30 and above: a failure of it on a loaded machine is run
  again before it is believed.

## Directions for 07 to 15 (Fable, 2026-11-24)

What each lesson's code is to try, set before the code agents start. A
measurement that says otherwise changes the lesson, not the claim; the
change is recorded in NOTES.md as 03.03's and 05.04's are. No weights
are shipped: a recorded long run ships its config, log, curve and text
samples, and a later lesson that needs a trained model trains a small
one in its own Run it, or uses the learner's checkpoint when it is there.

07, language models. Text: Tiny Shakespeare, shipped (a data file),
split by position into train, validation and test. Scores in bits per
character from 07.01 on.
- 07.01: the ladder of losses to beat: equal chances, single-character
  counts, pairs. Logarithms, probability and cross-entropy as bits
  arrive here. Shannon (1951) is the paper: his n-gram numbers beside
  ours, on a different alphabet and text, said so.
- 07.02: the failure is counting with longer contexts: the table grows,
  most of it is empty, held-out bits rise. Bengio et al. (2003):
  embeddings and a network over the same context, against the best
  smoothed count model, several seeds.
- 07.03: a recurrent cell written by hand (checked against PyTorch's),
  bits against 07.02; then how it forgets: recall of a symbol after T
  steps, accuracy and the size of the gradient against T.
- 07.04: Bahdanau et al. (2015), figure 2: an encoder and decoder
  copying a sequence through one vector gets worse with length; with
  attention over the encoder's states it does not. The weights, drawn.

08, the transformer, `models/gpt.py`, shaped from the start so that
09.03 can load GPT-2's weights into it (its layers, GELU, tied
embedding, learned positions).
- 08.01: attention inside one sequence, one head, causal mask. The
  failure is no mask: the loss falls to nothing and the samples are
  noise. A test: changing a later token leaves earlier outputs alone.
- 08.02: heads, the MLP, the residual stream, layer norm (04.04, 04.05
  reused); one head against several at equal size, as found.
- 08.03: without positions the next-character guess is the same for
  any order of the earlier characters (an exact test); bits with and
  without.
- 08.04: the module's long run, Shakespeare, against 07's ladder;
  AdamW, warmup and cosine from 03; where validation loss turns up.
- 08.05: Holtzman et al. (2020): greedy, plain sampling, temperature,
  top-k and top-p, measured by repetition and by the model's own
  perplexity of what it wrote beside its perplexity of held-out text.

09, GPT-2.
- 09.01: the failure is a vocabulary: characters make contexts short,
  words leave unknown words (counted). Sennrich et al. (2016): a BPE
  trainer on bytes; bytes per token against vocabulary size; any UTF-8
  text round-trips (non-ASCII test strings written as escapes).
- 09.02: GPT-2's vocabulary and merges, fetched and pinned; the same
  ids as tiktoken (test side) on a large and awkward corpus. The
  splitting pattern needs Unicode classes Python's `re` lacks: the
  standard library only, no `regex` module.
- 09.03: `model.safetensors` read by lab/safetensors.py into 08's GPT;
  logits equal to the reference's (transformers, test side). Then
  08.05's measurements again on the real model, as found.
- 09.04: Eldan and Li (2023), spike 4: a fetched, pinned subset, the
  learner's own BPE, a model of a few million parameters, the module's
  long run. Their grading by GPT-4 is not run again; say so.

10, today's architecture: each change against the piece it replaced,
same parameter count, same budget, several seeds, on 08's GPT.
- 10.01 RMSNorm (quality and time, both measured); 10.02 rotary
  positions (the score depends on the offset only: an exact test;
  longer sequences than trained on, as found); 10.03 SwiGLU at equal
  parameters; 10.04 grouped-query attention, and SmolLM2-135M loaded
  with the reference's logits (spike 5, its tokenizer included); 10.05
  the table: one change at a time and all together, Welch's t.

11, fast: spike 6 decides the lesson list. CPU numbers on the page, an
Apple GPU as an aside. Each of 11.03 to 11.06 is "the same numbers,
sooner", with a test that the numbers are the same; where an
optimisation gives nothing on a laptop CPU, the lesson says so and
shows where it does.

12, fine-tuning, from 09.03's GPT-2.
- 12.01: a classification head (Radford et al., 2018): frozen body,
  fine-tuned body, and a small model from scratch, on a small labelled
  text set whose licence is read at the source and recorded in NOTICE.
- 12.02: LoRA (Hu et al., 2021), spike 7: against full fine-tuning,
  with the count of trained weights; merged weights give the same
  logits (a test).
- 12.03: instruction tasks made by code (so every answer can be
  checked exactly), a chat template, exact-match before and after.
- 12.04: what each fine-tune did to the loss on text it was not tuned
  on, full against LoRA.

13, experiments that hold up, on models the learner already has.
- 13.01: one claim from 03 or 10 with an untuned and then a tuned
  baseline, the same search budget for both. 13.02: standard errors,
  the bootstrap, paired runs, how many seeds a difference needs.
  13.03: choosing by the test set, shown with real runs and a second
  held-out set; duplicates between train and test, counted. 13.04:
  Kaplan et al. (2020): fit loss against size on models trained here,
  predict the next size, then train it. The module's long run.

14, grokking (Power et al., 2022), spike 8, the paper's own set-up.
14.01 the claims as predictions and the data; 14.02 the short run that
memorises; 14.03 the long run and the figure, several seeds; 14.04
weight decay and training fraction, and the report.

15, lessons without new code: the worked example is a result of this
track that was not expected (03.03's tie, 04.05's "about as well",
03.04's region that did not show), taken from question to write-up
with the experiments and the lab as they stand.

Order after 09: 10, 12, 13 and 14 in parallel; 11 after 10 (both
change `models/gpt.py`); 15 last.

## The shelf

A module goes on the shelf when it has a paper with a claim, a failure
to start from, a laptop-size experiment that tests the claim, and a real
thing to check against. In the outline now: looking inside, images from
noise, learning from reward, seeing with transformers, preferences,
phenomena. Considered and left off until wanted: embeddings and
retrieval (word2vec to RAG), agents and tool use, speech, graph
networks, RL fine-tuning of language models, distributed training.

## Spikes, before the lesson list of a module is fixed

Each is run by an agent and its numbers go in tracks/research/NOTES.md.
Where a spike fails, the lesson changes; the claim is never stretched.

1. Engine speed: an MNIST epoch on the numpy engine, well under 60 s.
2. 05.04: double descent visible from a sweep of under 30 minutes.
3. 06.04: which depth and width show plain against residual in under 60
   minutes on CPU.
4. 09.04: the model size and step count that give whole stories in under
   60 minutes on CPU.
5. 10.04: the candidate (SmolLM2-135M) loads and matches its reference.
6. 11: which optimisations give a repeatable gain on a laptop CPU and on
   an Apple GPU. The module's lesson list follows the measurements.
7. 12.02: LoRA on GPT-2 small inside the time budget.
8. 14: grokking in under 30 minutes on CPU with the paper's set-up.
9. Everything on macOS arm64 and on Linux x86 (Docker).

## Harness work (each its own piece, not while another session edits it)

- Outlines: a module's `Optional: yes` shows it under "Extensions" on the
  outline page and its sidebar, as a built track's extensions are shown;
  template and tests updated. The outline already carries the field.
- `./learn fetch <track> [name]`: pinned downloads into a cache, and
  verify's "missing".
- A Python track: pinned numpy and PyTorch versions for verify, `@build`
  regions in .py files, check-skeleton and check-timeline for scripts.
- Curve figures drawn from recorded logs.

## Build order for the agents

Lessons are written module by module, as soon as a group of modules has
working code (agreed by the owner, 2026-11-14), not after the whole
track's code is finished. Each code step below is followed at once by
its lessons, module READMEs and lesson art, in parallel by module, from
the finished code and NOTES.md.

0. Outline art for the 22 modules (the covers moved from the old outline
   to 00, 01, 04, 13, 14, 15 and 16 are redrawn or checked against the new
   text), into a generator of its own, `art/outlines/research_art.py`.
   The spikes and the harness work, in parallel.
1. Skeleton, `engine/`, `lab/` and modules 00 to 05, by one agent. Then
   their lessons.
2. Module 06 alone: it sets the PyTorch-era skeleton every later module
   uses (devices, data loading, `models/`). Then its lessons.
3. Modules 07, 08, 09 in order by one agent; then 10, 11, 12, 13 and 14
   in parallel, each in its own files. 15 has lessons and no code. Each
   module's lessons follow its code.
4. The shelf, one agent per module, in parallel, after the core, each
   with its lessons.
5. Review: full internal run, `./learn verify`, every lesson read on the
   site. Do not export or publish the site while the track is half built.

## Open, for the owner

- Size: the core came out at 16 modules and 70 lessons (the shelf adds 6
  and 26). Each module is a finish line of its own. If that is too long,
  10 (today's architecture) and 11 (fast) are the two that could move to
  the shelf without breaking anything after them.
- The inference outline builds a tokenizer and a GPT-2 forward pass too.
  Proposed: when that track is planned, it starts from this track's
  finished GPT, as dsa's `edit` starts from kilo.
