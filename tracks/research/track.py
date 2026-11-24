"""Track research: AI research, from a first experiment to your own result.

The project is Python 3 and numpy, nothing else:

    engine/        the learner's deep learning library, under PyTorch's names (import engine as torch)
    lab/           the runner: settings, seeds, logs, spread over seeds, SVG plots, checkpoints, checks
    data/          the data: points made here, MNIST read from a cache (data/fetch.py fills it)
    experiments/   one script per lesson, run from the project's top: python3 -m experiments.<name>

Every script that trains with tensors names its engine in one line, `import engine as torch`;
the tests run each on PyTorch too, by changing that line, and compare. PyTorch and the
safetensors library are used only here, by the tests, as the reference.

From 06.02 on the project's scripts import PyTorch themselves, and models/ holds the networks
they share; module 06's part of this file is at its end.

Fixtures (here) the lesson tests share:

    py(t, args, cwd=None, check=True)
                        python3 -B args in the project (t.root), the project and tests/ on its
                        path; a Result: .out .err .rc
    inside(t, test_file)
                        run the test file's inside(S) in a fresh python, S being tests/support.py
                        (differential checks against PyTorch); its AssertionError is the failure
    experiment(t, name, *settings, root=None)
                        python3 -m experiments.<name> settings... out=<scratch>; a Result with .runs,
                        the directory its runs went to; fails on a non-zero exit
    on_torch(t, name, *settings)
                        the same script on PyTorch: the project copied to scratch, the script's
                        `import engine as torch` line made `import torch`
    summaries(r, label="")
                        the summary.json of every seed of one setting of a run, by seed
    value(text, regex)  the float the regex's first group matches in text (Fail if none)
    need(t, "mnist")    Fail with "missing: ..." unless the dataset is in the cache, as a missing
                        QEMU fails the xv6 tests

Tests are internal. A lesson's test exercises that lesson's code first (its differential
checks, then its experiment), so with the lesson's regions cut out it fails at a stub:
NotImplementedError("NN.LL: <name> not written yet").
"""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys

from harness.core import Fail, lesson_key

TITLE = "AI research, from a first experiment to your own result"
KIND = "research"
SUMMARY = ("A deep learning engine written in numpy and held to PyTorch's gradients, then the papers "
           "that made networks train, each run again on a laptop.")

UPSTREAM = {
    "name": "PyTorch",
    "url": "https://github.com/pytorch/pytorch",
    "licence": "BSD-3-Clause",
    "owes": "No code. The engine uses PyTorch's names and argument order, and its gradients are "
            "checked against PyTorch's.",
    "derived": False,
}

# Files that may hold "@build NN.LL" regions, and what a cut region becomes: a region is a whole
# definition, and its title is the name it defines, so the stub defines that name and fails when
# called. (A region whose definition other code subclasses says @stub class <name>: pass.)
SOURCES = ["engine/*.py", "engine/*/*.py", "lab/*.py", "data/*.py", "experiments/*.py"]
STUBS = {".py": 'def {title}(*args, **kwargs): raise NotImplementedError("{id}: {title} not written yet")'}
# Not for learners: the notes for the lesson writers, and what a run leaves behind.
HIDDEN = ["NOTES.md", "runs/*"]
# Files with no regions, and the lesson each comes with (every other file comes with its first region).
FILES_FROM = {
    "lab/__init__.py": "00.02",
    "engine/__init__.py": "02.01",
    "engine/nn/__init__.py": "02.04",
    "data/fetch.py": "03.01",
    "experiments/deep_stats.py": "04.01",
}

TESTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests")
PACKAGES = ("engine", "lab", "data", "experiments")


# ---------------------------------------------------------------- build and run

# What "building" a Python project means here: every .py file compiles, and the packages the
# project has so far import.
CHECK = ("import importlib, os, pathlib\n"
         "for p in sorted(pathlib.Path('.').rglob('*.py')):\n"
         "    compile(p.read_text(), str(p), 'exec')\n"
         "for name in ('engine', 'lab', 'data'):\n"
         "    if os.path.isdir(name):\n"
         "        importlib.import_module(name)\n")


def prepare(root):
    return [sys.executable, "-B", "-c", CHECK]


def build(t):
    t.run(prepare(t.root))


def experiments_in(root):
    d = os.path.join(root, "experiments")
    return sorted(f[:-3] for f in os.listdir(d) if f.endswith(".py")) if os.path.isdir(d) else []


def run_argv(root, args=()):
    """./learn run research --at 03.01 -- mnist_lr "lrs=[0.1]" runs python3 -m experiments.mnist_lr
    with those settings in the project's directory (experiments/mnist_lr.py and experiments.mnist_lr
    work too); with nothing after --, a shell there."""
    names = experiments_in(root)
    if not args:
        hint = (f"Run an experiment with python3 -m experiments.<name> (here: {', '.join(names) or 'none yet'}); "
                f"exit leaves this shell.")
        return ["/bin/sh", "-c", 'echo "$0"; exec "${SHELL:-/bin/sh}"', hint]
    name = args[0]
    if name.endswith(".py"):
        name = name[:-3]
    name = name.replace("/", ".")
    if name.startswith("experiments."):
        name = name[len("experiments."):]
    if name == "data.fetch":
        return [sys.executable, "-B", "-m", "data.fetch"] + list(args[1:])
    if name not in names:
        msg = f"no experiment {args[0]} at this lesson; the experiments here: {', '.join(names) or 'none'}"
        return [sys.executable, "-c", "import sys; sys.exit(sys.argv[1])", msg]
    return [sys.executable, "-B", "-m", f"experiments.{name}"] + list(args[1:])


# Without a prompt, seconds of quiet that mean "done". An experiment prints nothing while a seed
# trains: the longest quiet stretch of a run on any page is about 19 s on the machine in NOTES.md
# (03.03's adam, with three other runs going), and no Run it may take over 60 s (plans/research.md,
# Decisions: Time), so no stretch can either. Every run ends at the shell's prompt, which ends the
# wait at once, so the long settle costs nothing when a run finishes.
VERIFY_SETTLE = 60.0


def verify_tools():
    """What replaying a lesson needs: python3 with numpy. (MNIST, from 03.01 on, is a download, not a
    tool: see NOTES.md.) Lessons from 06.02 on need PyTorch too, and 06.03 on CIFAR-10: see
    pytorch_era_tools() below."""
    try:
        import numpy  # noqa: F401
        have_numpy = sys.executable
    except ImportError:
        have_numpy = None
    return {"python3": sys.executable, "numpy": have_numpy, **pytorch_era_tools()}


# ---------------------------------------------------------------- the shared fixtures

class Result:
    def __init__(self, argv, r, runs=None):
        self.argv, self.out, self.err, self.rc, self.runs = argv, r.stdout, r.stderr, r.returncode, runs

    def __repr__(self):
        return (f"$ {' '.join(self.argv)}\nrc={self.rc}\n--- stdout\n{self.out[-2500:]}\n"
                f"--- stderr\n{self.err[-2500:]}")


def _root(t):
    return t if isinstance(t, str) else t.root


def _env(root):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([root, TESTS_DIR])
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def py(t, args, cwd=None, check=True, timeout=900, root=None):
    root = root or _root(t)
    argv = [sys.executable, "-B"] + list(args)
    try:
        r = subprocess.run(argv, cwd=cwd or root, env=_env(root), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise Fail(f"{' '.join(argv)} did not finish in {timeout}s")
    res = Result(argv, r)
    if check and res.rc != 0:
        raise Fail(f"exit status {res.rc}:\n{res}")
    return res


def inside(t, test_file, name="inside"):
    """Run test_file's inside(S) in a fresh python on the project under test."""
    code = (f"import runpy, support\n"
            f"runpy.run_path({os.path.abspath(test_file)!r}, run_name='inside')[{name!r}](support)\n")
    r = py(t, ["-c", code], check=False)
    if r.rc != 0:
        lines = [l for l in r.err.strip().splitlines() if l.strip()]
        raise Fail(f"{os.path.basename(test_file)} {name}(): {lines[-1] if lines else '(no output)'}\n"
                   f"{r.err[-2000:]}")
    return r.out


def experiment(t, name, *settings, root=None, timeout=900):
    runs = os.path.join(t.tmp, f"runs-{name}-{len(os.listdir(t.tmp))}")
    root = root or _root(t)
    r = py(t, ["-m", f"experiments.{name}"] + [str(s) for s in settings] + [f"out={runs}"], check=False,
           root=root, timeout=timeout)
    r.runs = os.path.join(runs, name)
    if r.rc != 0:
        raise Fail(f"experiments.{name} failed:\n{r}")
    return r


def on_torch(t, name, *settings, timeout=900):
    """The experiment, unchanged but for its engine line, on PyTorch."""
    copy = os.path.join(t.tmp, "on-torch")
    if not os.path.isdir(copy):
        os.makedirs(copy)
        for pkg in PACKAGES:
            src = os.path.join(_root(t), pkg)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(copy, pkg), ignore=shutil.ignore_patterns("__pycache__"))
    path = os.path.join(copy, "experiments", f"{name}.py")
    with open(path) as f:
        lines = f.read().split("\n")
    at = [i for i, l in enumerate(lines) if l.startswith("import engine as torch")]
    if len(at) != 1:
        raise Fail(f"experiments/{name}.py should name its engine in one line, 'import engine as torch'")
    lines[at[0]] = "import torch"
    with open(path, "w") as f:
        f.write("\n".join(lines))
    return experiment(t, name, *settings, root=copy, timeout=timeout)


def summaries(r, label=""):
    """The summary.json of every seed of one setting, in seed order."""
    d = os.path.join(r.runs, label) if label else r.runs
    seeds = sorted((int(m.group(1)), m.group(0)) for m in (re.match(r"seed(\d+)$", n) for n in os.listdir(d)) if m)
    out = []
    for _, s in seeds:
        with open(os.path.join(d, s, "summary.json")) as f:
            out.append(json.load(f))
    return out


def value(text, regex):
    m = re.search(regex, text, re.M)
    if not m:
        raise Fail(f"no {regex!r} in the output:\n{text[-2500:]}")
    return float(m.group(1))


def cache_dir():
    return os.environ.get("LEARN_CACHE") or os.path.join(os.path.expanduser("~"), ".cache", "systems-from-scratch")


MNIST_FILES = {"train-images-idx3-ubyte.gz": 9912422, "train-labels-idx1-ubyte.gz": 28881,
               "t10k-images-idx3-ubyte.gz": 1648877, "t10k-labels-idx1-ubyte.gz": 4542}


def have_mnist():
    d = os.path.join(cache_dir(), "mnist")
    return all(os.path.isfile(os.path.join(d, f)) and os.path.getsize(os.path.join(d, f)) == n
               for f, n in MNIST_FILES.items())


def need(t, dataset="mnist"):
    if dataset == "cifar10":
        return need_cifar10(t)                  # module 06's part of this file, at the end
    if dataset != "mnist":
        raise Fail(f"no dataset {dataset!r}")
    if not have_mnist():
        raise Fail(f"missing: MNIST is not in {os.path.join(cache_dir(), 'mnist')}. Fetch it once with "
                   f"python3 -m data.fetch mnist, run in tracks/research/")


# ---------------------------------------------------------------- the project at each lesson
#
# Internal: ./learn check-timeline research writes the project as the site shows it at each lesson
# (harness/timeline.py), builds it (prepare: everything compiles and imports) and starts a shell
# in it. The steps run every experiment the project has by then, in a short version of itself,
# and check the last line it prints and that it exits 0; check which names the engine has (each
# name comes with its lesson); and check that what a later lesson brings is an ordinary error
# before it. No step may print a Python traceback.

TIMELINE_FAIL = [r"Traceback \(most recent call last\)", r"not written yet", r"Segmentation fault"]

# name: (the lesson it comes with, settings for a short run, what its last line says)
EXPERIMENTS = {
    "curve": ("00.01", ["steps=200", "seeds=2"], r"(runs in|run in|train loss \S+  test loss)"),
    "nudge": ("01.01", [], r"plot in "),
    "graph": ("01.02", [], r"largest difference from the nudge: \S+e-1\d"),
    "network": ("01.03", ["seeds=1"], r"seed 0: 37 weights"),
    "two_groups": ("01.04", ["seeds=1", "steps=5", "n_train=20", "n_test=20"], r"curves in "),
    "speed": ("02.01", ["n=2000", "repeats=1"], r"largest difference between their gradients: \S+e-1\d"),
    "broadcast": ("02.02", [], r"a batch of 5 rows plus a bias of 4"),
    "groups_tensors": ("02.03", ["steps=50", "seeds=1"], r"curves in "),
    "softmax": ("02.04", [], r"cross-entropy of equal scores over 10 classes: 2\.3026"),
    "checkpoint": ("02.05", ["steps=50"], r"after loading: the same scores, number for number: True"),
    "mnist_lr": ("03.01", ["lrs=[0.1]", "seeds=1", "n_train=2000"], r"curves in "),
    "momentum": ("03.02", ["seeds=1", "runs=[[0.05,0.9]]"], r"curves in "),
    "adam": ("03.03", ["models=['logistic']", "epochs=1", "seeds=1", "adam_lrs=[0.001]", "sgd_lrs=[0.1]"],
             r"curves in "),
    "adamw": ("03.04", ["epochs=1", "grid_lrs=[0.001]", "adam_wds=[0.0]", "adamw_wds=[0.1]", "seeds=1"],
              r"settings within"),
    "schedule": ("03.05", ["epochs=1", "seeds=1", "hidden=32", "runs=[['cosine',0.003,100]]"], r"curves in "),
    "deep_stats": ("04.01", ["seeds=1", "depth=6"], r"pictures in "),
    "init": ("04.02", ["seeds=1", "depth=6"], r"picture in "),
    "batchnorm": ("04.03", ["steps=100", "every=50", "seeds=1", "deep_lrs=[0.01]", "depth=4"], r"lr 0\.01 +batch norm"),
    "layernorm": ("04.04", ["steps=100", "seeds=1", "settings=[[2,0.02]]"], r"4\. batches of +2"),
    "residual": ("04.05", ["seeds=1", "depths=[4,6]"], r"residual: 6 layers against 4"),
    "bugs": ("04.06", ["seeds=1", "steps=50", "one_batch_steps=50"], r"eval in train mode"),
    "random_labels": ("05.01", ["seeds=1", "epochs=5"], r"curves in "),
    "regularise": ("05.02", ["seeds=1", "epochs=2"], r"both against neither"),
    "augment": ("05.03", ["seeds=1", "epochs=2", "shifts=[0,1]"], r"shifts up to 1 against none"),
    "double_descent": ("05.04", ["seeds=1", "widths=[50,1000,2000]"], r"curve in "),
}
MNIST_FROM = "03.01"
SHORT_BEFORE = {"curve": {"00.01": [], "00.02": ["steps=200"]}}      # its settings before 00.03

# The names each namespace of the engine gains, and the lesson they come with.
NAMES = {
    "engine": {"02.01": "Tensor tensor from_numpy zeros ones zeros_like ones_like float32 float64 int64 bool "
                        "exp log tanh relu tensors",
               "02.02": "autograd", "02.03": "no_grad matmul", "02.04": "nn", "02.05": "manual_seed randn rand",
               "03.01": "optim", "04.03": "sigmoid"},
    "nn": {"02.04": "Tensor functional", "02.05": "Parameter Module Linear ReLU Tanh Sequential",
           "04.02": "init", "04.03": "BatchNorm1d Sigmoid", "04.04": "LayerNorm", "05.02": "Dropout"},
    "F": {"02.04": "Tensor relu tanh log_softmax softmax cross_entropy", "05.02": "dropout"},
    "optim": {"03.01": "Optimizer SGD", "03.03": "Adam", "03.04": "AdamW", "03.05": "lr_scheduler"},
}
NAMES_CODE = (
    "import types, engine\n"
    "def names(ns):\n"
    "    return ' '.join(sorted(k for k, v in vars(ns).items() if not k.startswith('_') and not\n"
    "                    (isinstance(v, types.ModuleType) and not v.__name__.startswith('engine.'))))\n"
    "spaces = [('engine', engine)]\n"
    "if hasattr(engine, 'nn'):\n"
    "    spaces += [('nn', engine.nn), ('F', engine.nn.functional)]\n"
    "if hasattr(engine, 'optim'):\n"
    "    spaces.append(('optim', engine.optim))\n"
    "for name, ns in spaces:\n"
    "    print(name + ':', names(ns))\n")


def timeline_run(root):
    return ["/bin/sh"]


def sh_step(command, regex, status=0):
    """One command for the timeline's shell: (what to type, what must come back): regex somewhere in
    its output, then its exit status."""
    return (f'{command}; echo "@@ $?"', rf"(?s){regex}.*?@@ {status}\r?\n")


def _python(*args):
    return " ".join(shlex.quote(a) for a in [sys.executable, "-B"] + list(args))


def _code(code):
    """python3 -c running code, as one line of shell."""
    return _python("-c", f"exec({code!r})")


def _names_at(k):
    out = {}
    for space, by_lesson in NAMES.items():
        got = sorted(n for lid, names in by_lesson.items() if lesson_key(lid) <= k for n in names.split())
        if got:
            out[space] = got
    return out


def timeline_boot(lesson_id):
    k = lesson_key(lesson_id)
    steps = []
    for name, (lid, settings, last) in EXPERIMENTS.items():
        if lesson_key(lid) > k:
            continue
        settings = SHORT_BEFORE.get(name, {}).get(lesson_id, settings) if k < (0, 3) else settings
        command = _python("-m", f"experiments.{name}", *settings)
        data = DATASET_OF.get(name, "mnist" if lesson_key(lid) >= lesson_key(MNIST_FROM) else None)
        if data and not have_dataset(data):
            steps.append(sh_step(command + " 2>&1", rf"{data} is missing: .*python3 -m data\.fetch {data}", 1))
            continue
        steps.append(sh_step(command, last))
    if k >= (2, 1):
        expect = "".join(f"{space}: {' '.join(names)}\r?\n" for space, names in _names_at(k).items())
        steps.append(sh_step(_code(NAMES_CODE), "^" + expect))
    if k >= (0, 2):
        steps.append(sh_step(_python("-m", "experiments.curve", "lrr=1") + " 2>&1",
                             r"curve: no setting 'lrr' \(settings: ", 2))
    # what a later lesson brings is an ordinary error before it
    broadcast = ("import engine as t\n"
                 "a = t.tensor([[1.0], [2.0]], requires_grad=True)\n"
                 "try:\n"
                 "    (a + t.tensor([[1.0, 2.0]])).backward(t.ones(2, 2))\n"
                 "    print('gradient', tuple(a.grad.shape))\n"
                 "except ValueError as e:\n"
                 "    print('ValueError:', e)\n")
    if (2, 1) <= k < (2, 2):
        steps.append(sh_step(_code(broadcast), r"ValueError: a gradient of shape \(2, 2\) for a tensor of shape \(2, 1\)"))
    elif k >= (2, 2):
        steps.append(sh_step(_code(broadcast), r"gradient \(2, 1\)"))
    momentum = ("import engine as t\n"
                "p = t.tensor([1.0], requires_grad=True)\n"
                "try:\n"
                "    t.optim.SGD([p], lr=0.1, momentum=0.9)\n"
                "    print('momentum: ok')\n"
                "except TypeError as e:\n"
                "    print('TypeError:', e)\n")
    if (3, 1) <= k < (3, 2):
        steps.append(sh_step(_code(momentum), r"TypeError: .*unexpected keyword argument 'momentum'"))
    elif k >= (3, 2):
        steps.append(sh_step(_code(momentum), r"momentum: ok"))
    return steps


# ---------------------------------------------------------------- module 06: images, then PyTorch
#
# Kept apart from the tables above, which modules 00 to 05 fill. 06.01 is the last lesson that
# adds to the engine; from 06.02 on, scripts say `import torch` (see NOTES.md, "Conventions from
# 06.02 on").

EXPERIMENTS.update({
    "conv": ("06.01", ["seeds=1", "n_train=1000", "epochs=1", "n_test=400", "shifts=[0,2]"],
             r"convolutional +\S+ .*unshuffled, t = "),
    "switch": ("06.02", ["seeds=1", "steps=2", "width=8", "batch=16"], r"one pass over 50,000 images would take: "),
    "cifar": ("06.03", ["seeds=1", "n_train=200", "n_test=100", "epochs=1"], r"s of training and scoring on cpu"),
    "resnet": ("06.04", ["seeds=1", "n_train=64", "n_test=64", "epochs=1"], r"minutes of training on cpu"),
})
NAMES["nn"]["06.01"] = "Conv2d MaxPool2d Flatten"
NAMES["F"]["06.01"] = "conv2d max_pool2d"

# models/ (06.02 on): the networks experiments share. Its files hold regions; its __init__.py none.
SOURCES.append("models/*.py")
FILES_FROM["models/__init__.py"] = "06.02"
PACKAGES = PACKAGES + ("models",)

# The dataset each experiment needs, where it is not MNIST (every experiment from 03.01 on is MNIST's
# unless named here): check-timeline expects the "missing" line instead of a run without it.
DATASET_OF = {"switch": None, "cifar": "cifar10", "resnet": "cifar10"}

# The long run of 06.04, recorded: experiments/resnet.py's runs, written with out=experiments/recorded
# (config.json, log.jsonl and summary.json for every network and seed, and the curves). No regions;
# shown as data (the first lines of each), whole in the project's files.
FILES_FROM["experiments/recorded/*"] = "06.04"
DATA = {"experiments/recorded/*": "the long run of experiments/resnet.py (06.04), recorded on the machine in NOTES.md"}

CIFAR10_FILES = {"data_batch_1.bin": 30730000, "data_batch_2.bin": 30730000, "data_batch_3.bin": 30730000,
                 "data_batch_4.bin": 30730000, "data_batch_5.bin": 30730000, "test_batch.bin": 30730000,
                 "batches.meta.txt": 61}


def have_dataset(name):
    """Is the dataset in the cache, every file at its size? (data/fetch.py checks the SHA-256 too.)"""
    if name == "mnist":
        return have_mnist()
    files = {"cifar10": CIFAR10_FILES}[name]
    d = os.path.join(cache_dir(), name)
    return all(os.path.isfile(os.path.join(d, f)) and os.path.getsize(os.path.join(d, f)) == n for f, n in files.items())


def need_cifar10(t):
    if not have_dataset("cifar10"):
        raise Fail(f"missing: CIFAR-10 is not in {os.path.join(cache_dir(), 'cifar10')}. Fetch it once with "
                   f"python3 -m data.fetch cifar10, run in tracks/research/")


def _have_torch():
    import importlib.util
    return importlib.util.find_spec("torch") is not None


# The empty programs pytorch_era_tools writes, and what says this machine has each.
TOOLS = {"torch": _have_torch, "cifar10": lambda: have_dataset("cifar10")}


def pytorch_era_tools():
    """What verify_tools adds for the lessons from 06.02 on. verify_tools cannot name a tool for
    some lessons only, and a session's needs= looks for a program on PATH, not for a Python package
    or a download. So, for each of these that this machine has, an empty program of that name in
    build/tools/research/, whose folder verify then puts on PATH: "torch" when this python imports
    torch, "cifar10" when CIFAR-10 is in the cache (a stale one is removed). A session from 06.02 on
    says needs="torch", from 06.03 on needs="torch cifar10": on a machine without them its lesson is
    "missing", as a missing QEMU makes an xv6 lesson, while every lesson before 06.02 still replays.
    Each program is written only when it is not there already, so verify's cache stays valid.
    Later modules add their downloads to TOOLS (module 09: gpt2, tinystories)."""
    from harness.core import ROOT
    where = os.path.join(ROOT, "build", "tools", "research")
    have = {name: check() for name, check in TOOLS.items()}
    out = {}
    for name, ok in have.items():
        path = os.path.join(where, name)
        if not ok:
            if os.path.exists(path):
                os.remove(path)
            continue
        text = f"#!/bin/sh\n# {name} is on this machine: written by tracks/research/track.py for ./learn verify\nexit 0\n"
        try:
            with open(path) as f:
                same = f.read() == text
        except OSError:
            same = False
        if not same:
            os.makedirs(where, exist_ok=True)
            with open(path, "w") as f:
                f.write(text)
            os.chmod(path, 0o755)
        out[name] = path
    return out


# ---------------------------------------------------------------- module 07: language models
#
# Kept apart from the tables above, as module 06's part is. The text, Tiny Shakespeare, ships with the
# project (data/tinyshakespeare.txt, a data file: see NOTES.md, Data), so no experiment of the module
# needs a download; 07.01 is numpy only, 07.02 on import torch.

EXPERIMENTS.update({
    "bigram": ("07.01", [], r"chosen: k = 0\.1\r?\n"),
    "nplm": ("07.02", ["contexts=[2]", "seeds=1", "steps=20", "orders=[0,1,2]", "length=20"],
             r"s of counting, training and scoring on cpu"),
    "rnn": ("07.03", ["seeds=1", "steps=5", "recall_steps=5", "delays=[2]", "reads=[0,4]", "radii=[1.0]", "back=[0,4]",
                      "orders=2", "drawn=20"], r"s of training and scoring on cpu"),
    "attention": ("07.04", ["seeds=1", "steps=5", "lengths=[2,5]", "tested=20", "examples=[5]", "shown=5"],
                  r"s of training and scoring on cpu"),
})
DATASET_OF.update({"bigram": None, "nplm": None, "rnn": None, "attention": None})

# The text: shipped whole, shown on the site as data (its first lines).
FILES_FROM["data/tinyshakespeare.txt"] = "07.01"
DATA["data/tinyshakespeare.txt"] = "Tiny Shakespeare, from Andrej Karpathy's char-rnn, byte for byte (see NOTES.md)"

# The long run of 07.02, recorded as 06.04's is (experiments/nplm.py with out=experiments/recorded). 06.04's glob,
# "experiments/recorded/*", matches these files too, and the first glob that matches a file places it: so the
# narrower glob goes first.
FILES_FROM = {"experiments/recorded/nplm/*": "07.02", **FILES_FROM}
DATA["experiments/recorded/nplm/*"] = "the long run of experiments/nplm.py (07.02), recorded on the machine in NOTES.md"


# ---------------------------------------------------------------- module 08: the transformer, a GPT
#
# Kept apart from the tables above, as modules 06 and 07's parts are. models/gpt.py is built up over 08.01 to 08.03
# (regions, and @from blocks where a later lesson changes code an earlier one wrote), and experiments/language.py
# is the loop the module's experiments share. The text ships with the project, so nothing needs a download.

EXPERIMENTS.update({
    "self_attention": ("08.01", ["seeds=1", "steps=5", "sizes=[16]", "length=20", "orders=2"],
                       r"s of training and scoring on cpu"),
    "heads": ("08.02", ["seeds=1", "steps=5", "layers=2"], r"s of training and scoring on cpu"),
    "positions": ("08.03", ["seeds=1", "steps=5", "layers=2", "orders=2", "longer=[2]"],
                  r"s of training and scoring on cpu"),
    "gpt": ("08.04", ["seeds=1", "steps=6", "layers=1", "width=16", "context=16", "every=2", "held=4", "orders=2",
                      "length=20"], r"s of counting, training and scoring on cpu"),
    "sampling": ("08.05", ["seeds=1", "steps=5", "prompts=2", "length=8", "context=16", "prompt=8", "checkpoint=none"],
                 r"s of training, sampling and scoring on cpu"),
})
DATASET_OF.update({"self_attention": None, "heads": None, "positions": None, "gpt": None, "sampling": None})

# The long run of 08.04, recorded as 06.04's and 07.02's are (experiments/gpt.py with out=experiments/recorded): every
# config.json, log.jsonl and summary.json, the curves and what it printed; not its checkpoint (no weights are shipped).
# As module 07's part says, the first glob that matches a file places it, so this narrower one goes first too.
FILES_FROM = {"experiments/recorded/gpt/*": "08.04", **FILES_FROM}
DATA["experiments/recorded/gpt/*"] = "the long run of experiments/gpt.py (08.04), recorded on the machine in NOTES.md"
# The run writes its checkpoint beside the record; a learner who runs it again gets one there. It is weights, not
# part of the record: never shown or materialized, and not committed.
HIDDEN.append("experiments/recorded/*/model.safetensors")


# ---------------------------------------------------------------- module 09: GPT-2, the tokenizer and the real weights
#
# Kept apart from the tables above, as modules 06 to 08's parts are. tokens/ (09.01 on) is a package of its own, as
# models/ is: byte pair encoding (bpe.py) and GPT-2's tokenizer (gpt2.py). Not "tokenizers", which would hide the
# installed library of that name. 09.01 needs no download; 09.02 and 09.03 need GPT-2's files (python3 -m data.fetch
# gpt2), 09.04 TinyStories (python3 -m data.fetch tinystories).

SOURCES.append("tokens/*.py")
FILES_FROM["tokens/__init__.py"] = "09.01"
FILES_FROM["experiments/tokenizer.py"] = "09.02"          # no regions: its lesson's code is tokens/gpt2.py
PACKAGES = PACKAGES + ("tokens",)

EXPERIMENTS.update({
    "bpe": ("09.01", ["seeds=1", "steps=5", "layers=1", "width=16", "context=16", "sizes=[256,300]", "vocab=300",
                      "windows=10", "simple_merges=1"], r"s of counting, training and scoring on cpu"),
    "tokenizer": ("09.02", ["repeats=1", "size=300"], r"s of reading, training and encoding on cpu"),
    "gpt2": ("09.03", ["test_tokens=300", "warm=16", "wrong_windows=1", "prompts=2", "prompt_tokens=8", "length=6",
                       "seeds=1", "greedy=4"], r"s of loading, scoring and sampling on cpu"),
    "tinystories": ("09.04", ["seeds=1", "steps=5", "layers=1", "width=16", "heads=2", "context=16", "every=2", "held=4",
                              "held_stories=20", "samples=2", "length=20", "checkpoint=none"],
                    r"s of tokenising, training, scoring and telling on cpu"),
})
DATASET_OF.update({"bpe": None, "tokenizer": "gpt2", "gpt2": "gpt2", "tinystories": "tinystories"})

# The downloads of module 09 (data/fetch.py has their SHA-256s too), file by file with their sizes, and their names
# in a test's line.
DATASET_FILES = {
    "gpt2": {"vocab.json": 1042301, "merges.txt": 456318, "model.safetensors": 548105171},
    "tinystories": {"train.txt": 67108864, "valid.txt": 19447282},
}
DATASET_NAMES = {"gpt2": "GPT-2 (its vocabulary, merges and weights)",
                 "tinystories": "TinyStories (64 MiB of its training stories, and its validation stories)"}
_have_before_09, _need_before_09 = have_dataset, need


def have_dataset(name):
    """Is the dataset in the cache, every file at its size? Module 09's downloads, then those before it."""
    if name not in DATASET_FILES:
        return _have_before_09(name)
    d = os.path.join(cache_dir(), name)
    return all(os.path.isfile(os.path.join(d, f)) and os.path.getsize(os.path.join(d, f)) == n
               for f, n in DATASET_FILES[name].items())


def need(t, dataset="mnist", skip=False):
    """As before for MNIST and CIFAR-10 (a test fails with "missing: ..."). For module 09's downloads, with skip, a
    test that lacks one prints a line saying so and is told False (it then skips the checks that need it); else
    True."""
    if dataset not in DATASET_FILES:
        return _need_before_09(t, dataset)
    if have_dataset(dataset):
        return True
    message = (f"{DATASET_NAMES[dataset]} is not in {os.path.join(cache_dir(), dataset)}. Fetch it once with "
               f"python3 -m data.fetch {dataset}, run in tracks/research/")
    if not skip:
        raise Fail(f"missing: {message}")
    print(f"      skipped what needs it: {message}")
    return False


TOOLS["gpt2"] = lambda: have_dataset("gpt2")
TOOLS["tinystories"] = lambda: have_dataset("tinystories")


def _have_tiktoken():
    """09.02's page compares the learner's ids with tiktoken's when tiktoken is installed (the project never imports
    it): that session says needs="gpt2 tiktoken", so without tiktoken the lesson is "missing", not failed."""
    import importlib.util
    return importlib.util.find_spec("tiktoken") is not None


TOOLS["tiktoken"] = _have_tiktoken

# The long run of 09.04, recorded as 08.04's is (experiments/tinystories.py with out=experiments/recorded): every
# config.json, log.jsonl and summary.json, the curves, what it printed (its stories with it); not its checkpoint. The
# first glob that matches a file places it, so this narrower one goes first too.
FILES_FROM = {"experiments/recorded/tinystories/*": "09.04", **FILES_FROM}
DATA["experiments/recorded/tinystories/*"] = ("the long run of experiments/tinystories.py (09.04), recorded on the "
                                              "machine in NOTES.md")


# ---------------------------------------------------------------- module 10: today's architecture
#
# Kept apart from the tables above, as modules 06 to 09's parts are. models/gpt.py gains RMSNorm (10.01), Rotary
# (10.02), SwiGLU (10.03) and grouped-query attention (10.04), each chosen by an argument of GPT whose default is module
# 08's piece; experiments/language.py gains compare (10.01), the loop that trains GPTs differing in one piece alike.
# 10.04 loads SmolLM2-135M (models/smollm.py, tokens/smollm.py; lab/safetensors.py reads bfloat16): it needs
# python3 -m data.fetch smollm2. 10.05's long run is recorded in experiments/recorded/ablation/.

FILES_FROM["experiments/smollm.py"] = "10.04"          # no regions: its lesson's code is in models/, tokens/ and lab/

EXPERIMENTS.update({
    "rmsnorm": ("10.01", ["seeds=1", "steps=5", "layers=1", "width=16", "context=16", "repeats=2", "big=[2,8,16]"],
                r"s of timing, training and scoring on cpu"),
    "rotary": ("10.02", ["seeds=1", "steps=5", "layers=1", "width=16", "context=16", "longer=[2]"],
               r"s of training and scoring on cpu"),
    "swiglu": ("10.03", ["seeds=1", "steps=5", "layers=1", "width=16", "context=16"], r"s of training and scoring on cpu"),
    "smollm": ("10.04", ["seeds=1", "steps=5", "layers=1", "width=16", "context=16", "kv=[4,2]", "test_tokens=300",
                         "warm=16", "span=49", "greedy=4", "prompt_tokens=8", "length=4"],
               r"s of training, loading, scoring and sampling on cpu"),
    "ablation": ("10.05", ["seeds=1", "steps=5", "layers=1", "width=16", "context=16", "every=2", "held=4"],
                 r"s of training and scoring on cpu"),
})
DATASET_OF.update({"rmsnorm": None, "rotary": None, "swiglu": None, "smollm": "smollm2", "ablation": None})

# The download of 10.04 (data/fetch.py has the SHA-256s too), file by file with their sizes, and its name in a test's
# line. need(t, "smollm2") and have_dataset("smollm2") are module 09's, which read these dicts.
DATASET_FILES["smollm2"] = {"config.json": 704, "tokenizer.json": 2104556, "tokenizer_config.json": 3658,
                            "model.safetensors": 269060552}
DATASET_NAMES["smollm2"] = "SmolLM2-135M (its configuration, tokenizer and weights)"
TOOLS["smollm2"] = lambda: have_dataset("smollm2")


def _have_transformers():
    """10.04's page compares SmolLM2's logits and ids with transformers' when transformers is installed (the project
    never imports it): that session says needs="torch smollm2 transformers", so without it the lesson is "missing", not
    failed."""
    import importlib.util
    return importlib.util.find_spec("transformers") is not None


TOOLS["transformers"] = _have_transformers

# The long run of 10.05, recorded as 09.04's is (experiments/ablation.py with out=experiments/recorded): every row's
# config.json, log.jsonl and summary.json, the curves, the times and what it printed; no weights (it saves none). The
# first glob that matches a file places it, so this narrower one goes first too.
FILES_FROM = {"experiments/recorded/ablation/*": "10.05", **FILES_FROM}
DATA["experiments/recorded/ablation/*"] = ("the long run of experiments/ablation.py (10.05), recorded on the machine in "
                                           "NOTES.md")


# ---------------------------------------------------------------- module 14: reproduce a paper, grokking
#
# Kept apart from the tables above, as modules 06 to 08's parts are, and last in the file, so another module's part can
# sit before it. data/modular.py makes the paper's data (nothing to download); experiments/predictions.py holds the
# paper's claims as predictions, which claims.py prints and report.py (14.04) judges. experiments/arithmetic.py is the
# loop the module's scripts share (as language.py is module 08's); grokking.py has no region of its own, so it is placed
# here. Nothing in the module needs a download: needs="torch" from 14.02 on, 14.01 needs nothing but numpy.

EXPERIMENTS.update({
    "claims": ("14.01", ["seeds=1"], r"A run has learned the operation only if its validation accuracy is far above"),
    "grokking": ("14.02", ["seeds=1", "steps=5", "p=7"], r"s of training and scoring on cpu"),
    "ablations": ("14.04", [], r"s of training and reading on cpu"),
    "report": ("14.04", [], r"the report in "),
})
DATASET_OF.update({"claims": None, "grokking": None, "ablations": None, "report": None})
FILES_FROM["experiments/grokking.py"] = "14.02"

# The long runs, recorded as 06.04's, 07.02's and 08.04's are: grokking.py's (14.03, the figure) and ablations.py's
# (14.04), each with out=experiments/recorded: every config.json, log.jsonl and summary.json, the curves and what it
# printed. As module 07's part says, the first glob that matches a file places it, so these narrower ones go first.
FILES_FROM = {"experiments/recorded/grokking/*": "14.03", "experiments/recorded/ablations/*": "14.04", **FILES_FROM}
DATA["experiments/recorded/grokking/*"] = ("the long run of experiments/grokking.py (14.03), recorded on the machine in "
                                           "NOTES.md")
DATA["experiments/recorded/ablations/*"] = ("the runs of experiments/ablations.py (14.04), recorded on the machine in "
                                            "NOTES.md")


# ---------------------------------------------------------------- module 13: experiments that hold up
#
# Kept apart from the tables above, in one block at the end of the file, so that the parts other modules add at the
# same time stay whole when they are merged. Module 13's statistics are regions of lab/stats.py (13.01 to 13.04; lab/
# __init__.py re-exports them with one-line @from markers); its experiments are baseline (13.01, MNIST), errorbars
# (13.02, Tiny Shakespeare: nothing to fetch), fooled (13.03: MNIST; CIFAR-10 and TinyStories when fetched, each part
# skipped with a line naming the fetch command when not) and scaling (13.04, TinyStories). 13.02 and 13.04 have
# recorded runs (13.04's is the module's long run); their defaults read them.

EXPERIMENTS.update({
    "baseline": ("13.01", ["n_train=500", "n_val=500", "trials=2", "seeds=1", "epochs=1", "hidden=16"],
                 r"s of training and scoring on cpu"),
    "errorbars": ("13.02", ["seeds=2", "steps=4", "layers=1", "width=16", "context=16", "every=2", "resamples=100"],
                  r"s of training and scoring on cpu"),
    "fooled": ("13.03", ["runs=3", "ks=[1,3]", "n_train=300", "hidden=8", "epochs=1", "n_test=500"],
               r"s of training, searching and counting on cpu"),
    "scaling": ("13.04", ["widths=[8,16]", "largest=24", "steps=4", "every=2", "held=4", "held_stories=10", "context=16"],
                r"s of training, scoring and fitting on cpu"),
})
DATASET_OF.update({"baseline": "mnist", "errorbars": None, "fooled": "mnist", "scaling": "tinystories"})

# The recorded runs, as 08.04's and 14.03's are (each script with out=experiments/recorded): every config.json,
# log.jsonl and summary.json, the curves and what it printed; no weights. The first glob that matches a file places it
# (module 07's part says why), so these narrower ones go first.
FILES_FROM = {"experiments/recorded/errorbars/*": "13.02", "experiments/recorded/scaling/*": "13.04", **FILES_FROM}
DATA["experiments/recorded/errorbars/*"] = ("the runs of experiments/errorbars.py at 10 seeds a side (13.02), recorded "
                                            "on the machine in NOTES.md")
DATA["experiments/recorded/scaling/*"] = ("the long run of experiments/scaling.py (13.04), recorded on the machine in "
                                          "NOTES.md")


# ---------------------------------------------------------------- module 15: your own result
#
# Kept apart from the tables above, in one block at the end of the file, so that the parts other modules add at the
# same time stay whole when they are merged. experiments/question.py holds the question, what others found, the
# predictions written before any run and the code the module's three scripts share (15.01: pair, trained, judge,
# budget, read_runs; 15.02: choose, gaps); pilot.py (15.01) has no region of its own, so it is placed here; depth.py
# (15.02) is the experiment and paper.py (15.03) the paper written from its logs. Tiny Shakespeare ships with the
# project, so nothing needs a download: needs="torch". The pilot and the experiment are recorded; their defaults read
# the records, and paper.py reads nothing else.

EXPERIMENTS.update({
    "pilot": ("15.01", ["seeds=2", "steps=4", "every=2", "depths=[1,2]", "width=16", "context=16"],
              r"s of training and scoring on cpu"),
    "depth": ("15.02", ["seeds=2", "steps=4", "every=2", "width=16", "context=16", "rates=[0.003]"],
              r"s of training and scoring on cpu"),
    "paper": ("15.03", [], r"the paper in "),
})
DATASET_OF.update({"pilot": None, "depth": None, "paper": None})
FILES_FROM["experiments/pilot.py"] = "15.01"

# The recorded runs, as 13.02's and 14.03's are (each script with out=experiments/recorded): every config.json,
# log.jsonl and summary.json, the figures and what it printed; and the paper as paper.py wrote it from them. No weights.
# The first glob that matches a file places it (module 07's part says why), so these narrower ones go first.
FILES_FROM = {"experiments/recorded/pilot/*": "15.01", "experiments/recorded/depth/*": "15.02",
              "experiments/recorded/paper/*": "15.03", **FILES_FROM}
DATA["experiments/recorded/pilot/*"] = ("the pilot of experiments/pilot.py (15.01), recorded on the machine in "
                                        "NOTES.md")
DATA["experiments/recorded/depth/*"] = ("the experiment of experiments/depth.py (15.02), recorded on the machine in "
                                        "NOTES.md")
DATA["experiments/recorded/paper/*"] = "the paper experiments/paper.py (15.03) wrote from the two recorded runs"
