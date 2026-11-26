"""Track gpu: GPU kernels for LLM inference, from scratch.

Modules 00 and 01 run on the CPU, in C11 built by make with the host's cc: wb (the workbench:
rng.c, add.c, check.c, bench.c, wb.c) and mm (matrix multiply: matmul.c, matmul_simd.c,
matmul_blocked.c, matmul_threads.c, blas.c, mm.c). From module 02 the kernels are CUDA; those modules wait for a
machine with an NVIDIA GPU (plans/gpu.md, "The GPU machine").

Fixtures the lesson tests use (t is the test's context):

    flags(t)                   make -s flags in the tree: {"CFLAGS": [...], "SCALAR": [...],
                               "SIMD": [...], "BLAS": [...], "BLASLIBS": [...], "LDLIBS": [...]}
    exe(t, name, mode=None)    the path of wb or mm: ./name, or with GPU_SANITIZE=1 (mode
                               "address") the same sources built with AddressSanitizer and
                               UBSan outside the track, once per tree per run
    prog(t, name, argv, input="", mode=None, timeout=120)
                               wb or mm with argv: (status, stdout, stderr); fails on a
                               sanitizer report or when it does not stop in time
    driver(t, name, input, mode=None, timeout=300)
                               tests/NAME.c (rng_driver, add_driver, check_driver,
                               bench_driver, matmul_driver) built with the tree's sources and
                               run on input: its stdout, as lines; fails on any other exit
                               status, saying what it printed on stderr. mode "thread" builds
                               it with ThreadSanitizer
    build_with(t, name, sources, replace)
                               a program built from the tree's sources with some files
                               replaced ({"add.c": text}), in a scratch directory: its path
    warnings(t)                every source compiled with -std=c11 -Wall -Wextra -pedantic
                               -Werror and the Makefile's flags: what the compiler said, ""
    rng_u32s(seed, count), rng_f32s(seed, count), rng_fill(seed, n)
                               the generator again, in Python
    show_text(n, seed)         what wb show prints

Tests are internal. With a lesson's code cut out, its test fails at the stub: "gpu: NN.LL: <what>
not written yet", exit status 3. GPU_SANITIZE=1 runs every program and driver built with
AddressSanitizer and UBSan. 01.05's test always runs matmul_threads under ThreadSanitizer too;
GPU_TSAN=0 leaves that part out, for a machine where TSan cannot run (x86-64 under Rosetta: "FATAL:
ThreadSanitizer: unexpected memory mapping").
"""

import atexit
import os
import re
import shutil
import struct
import subprocess
import tempfile
import threading

try:
    from harness.core import Fail
except ImportError:          # loaded on its own
    class Fail(Exception):
        pass

TITLE = "GPU kernels for LLM inference, from scratch"
KIND = "gpu"
SUMMARY = ("The kernels an inference server like vLLM runs on the GPU, written by you and checked "
           "against a plain reference, starting from matrix multiply on the CPU.")

# What this track is built on (harness/web/views.py, upstreams()). No code is taken from any of them.
UPSTREAM = [
    {"name": "vLLM",
     "url": "https://github.com/vllm-project/vllm",
     "licence": "Apache-2.0",
     "owes": "No code. The kernels the track writes from module 02 on follow vLLM's at tag v0.2.0 "
             "(activation, RMS norm, rotary embedding, the block cache and paged attention), each read "
             "after the reader has written their own.",
     "derived": False},
    {"name": "flash-attention",
     "url": "https://github.com/Dao-AILab/flash-attention",
     "licence": "BSD-3-Clause",
     "owes": "No code. Attention over a whole prompt in tiles, with a running softmax, is its idea; "
             "module 07 reads it.",
     "derived": False},
    {"name": "llama2.c",
     "url": "https://github.com/karpathy/llama2.c",
     "licence": "MIT",
     "owes": "No code. The workbench's random numbers are its sampling generator (xorshift64*), "
             "written again from the algorithm, and its small model and plain C forward pass are the "
             "reference the later kernels are checked against.",
     "derived": False},
    {"name": "llm.c",
     "url": "https://github.com/karpathy/llm.c",
     "licence": "MIT",
     "owes": "No code. A second forward pass in hand-written CUDA, to read beside the track's own.",
     "derived": False},
]

# Files that may hold "@build NN.LL" regions (harness/workspace.py), and what a cut region becomes:
# todo() (@internal in rng.c, declared @internal in every header) prints "gpu: NN.LL: <what> not
# written yet" and exits 3.
SOURCES = ["*.c", "*.h"]
STUBS = {".c": 'todo("{id}", "{title}");'}
# Not for learners: the notes for the lesson writers, and what make builds.
HIDDEN = ["NOTES.md", "RESEARCH.md", "wb", "mm", "*.o", "*.dSYM/*"]
# When each file comes into the project (harness/timeline.py): a file with regions comes with its
# first region's lesson; the others are named here.
FILES_FROM = {
    "Makefile": "00.01",
    "rng.h": "00.01",
    "add.h": "00.01",
    "check.h": "00.02",
    "bench.h": "00.03",
    "matmul.h": "01.01",
}

HERE = os.path.dirname(os.path.abspath(__file__))


def build(t):
    t.run(["make", "-s"])


# ---------------------------------------------------------------- run it
#
# The track contract's optional hooks, all from the project's directory: prepare(root) builds
# it, run_argv(root) runs it (./learn run gpu --at NN.LL), bench(root) is ./learn bench gpu.

def prepare(root):
    return ["make", "-s"]


SAMPLES = [   # (the file that comes with the lesson, the lesson's sample command)
    ("mm.c", "./mm check && ./mm time"),
    ("bench.c", "./wb time"),
    ("check.c", "./wb check"),
    ("wb.c", "./wb show"),
]
NAMED = ("wb", "mm")


def run_argv(root, args=()):
    """With no args, the sample of the lesson the project stands at (the newest of its files
    names it), through sh -c from the project's directory: from 01.01, ./mm check && ./mm time.
    With args: wb or mm when the first names it (./learn run gpu -- wb show -s 7), else ./mm
    (./wb before mm exists) with them all."""
    args = list(args)
    if args:
        name = args[0][2:] if args[0].startswith("./") else args[0]
        if name in NAMED and os.path.exists(os.path.join(root, name + ".c")):
            return ["./" + name] + args[1:]
        return (["./mm"] if os.path.exists(os.path.join(root, "mm.c")) else ["./wb"]) + args
    command = next(c for f, c in SAMPLES if os.path.exists(os.path.join(root, f)))
    return ["/bin/sh", "-c", command]


def bench(root):
    """The benchmark: mm time, every variant; wb time from 00.03, before mm exists; before 00.03
    there is no timer yet, and it says so."""
    if os.path.exists(os.path.join(root, "mm.c")):
        return ["./mm", "time"]
    if os.path.exists(os.path.join(root, "bench.c")):
        return ["./wb", "time"]
    return ["/bin/sh", "-c", "echo 'gpu: nothing to time yet: the timer comes in 00.03 (wb time)' >&2; exit 2"]


# ---------------------------------------------------------------- the generator, in Python
#
# The same xorshift64* as rng.c, written again from its definition: the tests hold wb's numbers
# to it, and to llama2.c's reference values (RESEARCH.md, section 1.1).

MASK64 = (1 << 64) - 1


def _step(state):
    state ^= state >> 12
    state ^= (state << 25) & MASK64
    state ^= state >> 27
    return state, ((state * 0x2545F4914F6CDD1D) & MASK64) >> 32


def rng_u32s(seed, count):
    state, out = seed, []
    for _ in range(count):
        state, u = _step(state)
        out.append(u)
    return out


def f32(x):
    return struct.unpack("f", struct.pack("f", x))[0]


def rng_f32s(seed, count):
    return [f32((u >> 8) / 16777216.0) for u in rng_u32s(seed, count)]


def rng_fill(seed, n):
    return [f32(2 * f - 1) for f in rng_f32s(seed, n)]


def show_text(n, seed):
    """What wb show -n n -s seed prints."""
    a, b = rng_fill(seed, min(n, 4)), rng_fill(seed + 1, min(n, 4))
    s = [f32(x + y) for x, y in zip(a, b)]

    def row(name, xs):
        return f"{name:<4}" + "".join(" %10.6f" % x for x in xs) + "\n"
    return f"n = {n}, seed = {seed}\n" + row("a", a) + row("b", b) + row("add", s)


# ---------------------------------------------------------------- building, outside the track
#
# The programs make builds are ./wb and ./mm. The drivers (tests/*.c) and the sanitizer builds are
# compiled here, from the tree's sources with the flags its Makefile uses for each file (make -s
# flags), into directories of their own, once per tree and mode per run.

PROGRAMS = {
    "wb": ["wb.c", "rng.c", "add.c", "check.c", "bench.c"],
    "mm": ["mm.c", "rng.c", "check.c", "bench.c", "matmul.c", "matmul_simd.c", "matmul_blocked.c",
           "matmul_threads.c", "blas.c"],
}
DRIVERS = {
    "rng_driver": ["rng.c"],
    "add_driver": ["rng.c", "add.c"],
    "check_driver": ["rng.c", "check.c"],
    "bench_driver": ["rng.c", "bench.c"],
    "matmul_driver": ["rng.c", "check.c", "matmul.c", "matmul_simd.c", "matmul_blocked.c", "matmul_threads.c",
                      "blas.c"],
}
EXTRA = {"add.c": "SCALAR", "matmul.c": "SCALAR", "matmul_simd.c": "SIMD", "blas.c": "BLAS"}
MODES = {
    "plain": [],
    "address": ["-O1", "-g", "-fno-omit-frame-pointer", "-fsanitize=address,undefined",
                "-fno-sanitize-recover=all"],
    "thread": ["-O1", "-g", "-fsanitize=thread"],
}
SANITIZER = re.compile(r"AddressSanitizer|UndefinedBehaviorSanitizer|runtime error:|LeakSanitizer|"
                       r"ThreadSanitizer")

_lock = threading.Lock()
_flags = {}
_built = {}
_dirs = []


@atexit.register
def _clean():
    for d in _dirs:
        shutil.rmtree(d, ignore_errors=True)


def _scratch(prefix):
    d = tempfile.mkdtemp(prefix=prefix)
    _dirs.append(d)
    return d


def default_mode():
    return "address" if os.environ.get("GPU_SANITIZE") else "plain"


def flags(t, root=None):
    root = root or t.root
    with _lock:
        if root not in _flags:
            r = subprocess.run(["make", "-s", "flags"], cwd=root, capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                raise Fail(f"make -s flags failed:\n{r.stdout}{r.stderr}")
            got = {}
            for line in r.stdout.splitlines():
                key, _, rest = line.partition(" ")
                got[key] = rest.split()
            _flags[root] = got
        return _flags[root]


def _cc():
    return os.environ.get("HOSTCC", "cc")


def _compile(root, fl, mode, sources, out, extra_src=None):
    """Compile sources (paths under root) and extra_src (a path anywhere) with each file's flags,
    and link them into out."""
    objdir = out + ".o.d"
    os.makedirs(objdir, exist_ok=True)
    objs = []
    for src in list(sources) + ([extra_src] if extra_src else []):
        name = os.path.basename(src)
        obj = os.path.join(objdir, name[:-2] + ".o")
        argv = [_cc()] + fl["CFLAGS"] + fl.get(EXTRA.get(name, ""), []) + MODES[mode] + \
            ["-I", root, "-c", "-o", obj, src]
        r = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            raise Fail(f"compiling {name} failed:\n{' '.join(argv)}\n{r.stderr[-3000:]}")
        objs.append(obj)
    libs = fl.get("LDLIBS", []) + (fl.get("BLASLIBS", []) if "blas.c" in sources else [])
    argv = [_cc()] + MODES[mode] + ["-o", out] + objs + libs
    r = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise Fail(f"linking {os.path.basename(out)} failed:\n{' '.join(argv)}\n{r.stderr[-3000:]}")
    return out


def _built_path(t, kind, name, mode):
    key = (t.root, kind, name, mode)
    with _lock:
        if key in _built:
            return _built[key]
    fl = flags(t)
    out = os.path.join(_scratch(f"gpu-{mode}-"), name)
    if kind == "program":
        sources = [s for s in PROGRAMS[name] if os.path.exists(os.path.join(t.root, s))]
        _compile(t.root, fl, mode, sources, out)
    else:
        _compile(t.root, fl, mode, DRIVERS[name], out, os.path.join(HERE, "tests", name + ".c"))
    with _lock:
        _built[key] = out
    return out


def exe(t, name, mode=None):
    """./name of the tree under test, or the same program built in a sanitizer mode."""
    mode = mode or default_mode()
    if mode == "plain":
        return os.path.join(t.root, name)
    return _built_path(t, "program", name, mode)


def _run(argv, input, timeout, what, cwd):
    try:
        r = subprocess.run(argv, input=input.encode(), capture_output=True, timeout=timeout, cwd=cwd)
    except subprocess.TimeoutExpired:
        raise Fail(f"{what} did not stop within {timeout} s")
    out, err = r.stdout.decode("latin-1"), r.stderr.decode("latin-1")
    if SANITIZER.search(err):
        raise Fail(f"{what}: a sanitizer report:\n{err[-4000:]}")
    return r.returncode, out, err


def prog(t, name, argv, input="", mode=None, timeout=120):
    """wb or mm (or a program build_with made: its path) with argv, run in the test's scratch
    directory: (status, stdout, stderr)."""
    path = name if os.sep in name else exe(t, name, mode)
    what = f"{os.path.basename(name)} {' '.join(argv)}"
    return _run([path] + list(argv), input, timeout, what, t.tmp)


def driver(t, name, input, mode=None, timeout=300):
    """tests/NAME.c built with the tree's sources, on input: its stdout's lines."""
    mode = mode or default_mode()
    path = _built_path(t, "driver", name, mode)
    st, out, err = _run([path], input, timeout, name, t.tmp)
    if st != 0:
        raise Fail(f"{name} stopped with status {st}:\n{err[-3000:]}\n(its last output: {out[-500:]!r})")
    return out.splitlines()


def build_with(t, name, replace, mode=None):
    """The program name built from a copy of the tree's sources, with the files in replace
    ({"add.c": text}) written over theirs: its path."""
    mode = mode or default_mode()
    root = _scratch("gpu-patched-")
    for f in os.listdir(t.root):
        if f.endswith((".c", ".h")) or f == "Makefile":
            shutil.copy(os.path.join(t.root, f), os.path.join(root, f))
    for f, text in replace.items():
        with open(os.path.join(root, f), "w") as fh:
            fh.write(text)
    fl = flags(t)
    out = os.path.join(root, name + "-patched")
    return _compile(root, fl, mode, PROGRAMS[name], out)


def warnings(t):
    """Every source of the tree compiled with -Werror on top of the Makefile's flags for it."""
    fl = flags(t)
    said = []
    for src in sorted(f for f in os.listdir(t.root) if f.endswith(".c")):
        argv = [_cc()] + fl["CFLAGS"] + fl.get(EXTRA.get(src, ""), []) + \
            ["-Werror", "-fsyntax-only", "-I", t.root, src]
        r = subprocess.run(argv, cwd=t.root, capture_output=True, text=True, timeout=120)
        said.append((r.stdout + r.stderr).strip())
    return "\n".join(s for s in said if s)


def floats(words):
    """Hex floats (%a, or nan, inf) as Python floats."""
    return [float.fromhex(w) if "0x" in w.lower() else float(w) for w in words]


# ---------------------------------------------------------------- module 01: every variant, every shape

BLOCK_LINE = re.compile(r"^#define MM_BLOCK (\d+)", re.M)


def block_size(t):
    """MM_BLOCK, as the tree under test has it (matmul_blocked.c)."""
    with open(os.path.join(t.root, "matmul_blocked.c")) as f:
        m = BLOCK_LINE.search(f.read())
    if not m:
        raise Fail("matmul_blocked.c has no line #define MM_BLOCK N")
    return int(m.group(1))


def shapes(block):
    """The shapes every variant is held to matmul_ref on, as (m, k, n): every square size 1 to 67
    (so every k from 1 to 9: no p left over, and 1, 2 or 3 of them); forty seeded random ones,
    each side 1 to 200; one less, equal and one more than 4 and 8 (a vector of either width),
    than MM_BLOCK and than twice a multiple of MM_BLOCK and 8, on each side alone and on all
    three; k % 4 of 1, 2 and 3 with n % 8 of 1 to 7, small and across a tile; 1 x k x 1 and
    m x 1 x n; and a side of 0 (c empty, or all 0 when k is 0)."""
    import math
    import random
    out = [(s, s, s) for s in range(1, 68)]
    rng = random.Random(101)
    out += [(rng.randint(1, 200), rng.randint(1, 200), rng.randint(1, 200)) for _ in range(40)]
    both = 2 * (block * 8 // math.gcd(block, 8))
    for s in sorted({4, 8, block, both}):
        for x in (s - 1, s, s + 1):
            if x > 0:
                out += [(x, x, x), (x, 5, 3), (3, x, 5), (5, 3, x), (x, 9, x)]
    for kr in (1, 2, 3):
        for nr in range(1, 8):
            out += [(3, 4 + kr, 8 + nr), (block + 2, block + 4 + kr, block + 8 + nr)]
    out += [(1, 300, 1), (1, 1, 300), (300, 1, 1), (150, 1, 170), (1, 70, 9), (9, 70, 1)]
    out += [(0, 5, 7), (5, 0, 7), (5, 7, 0), (0, 0, 0), (0, 0, 5), (3, 0, 0), (0, 9, 0)]
    return out


def check_variant(t, name, mode=None, threads=None, every=1, offsets=(1, 3, 5)):
    """Variant name against matmul_ref on every shape of shapes() (every n-th one when every > 1),
    and again on some of them with a, b and c starting off an aligned address (offsets); a times I
    and I times a exactly a. With threads, matmul_thread_count is set first. Fails listing the
    first shapes that failed."""
    block = block_size(t)
    todo = shapes(block)[::every]
    text = f"threads {threads}\n" if threads is not None else ""
    asked = []
    for i, (m, k, n) in enumerate(todo):
        text += f"check {name} {m} {k} {n} {1000 + i}\n"
        asked.append(f"{m}x{k}x{n}")
    for off in offsets:
        text += f"offset {off}\n"
        for i, (m, k, n) in enumerate(todo[::9]):
            text += f"check {name} {m} {k} {n} {7 + i}\n"
            asked.append(f"{m}x{k}x{n} at offset {off}")
    text += "offset 0\n"
    for n in (1, 2, 7, 8, 9, block - 1, block + 1, 2 * block + 3):
        text += f"identity {name} {n} {n}\n"
        asked.append(f"identity {n}")
    lines = [l for l in driver(t, "matmul_driver", text, mode=mode)
             if not l.startswith(("threads ", "offset "))]
    if len(lines) != len(asked):
        raise Fail(f"{name}: matmul_driver answered {len(lines)} of {len(asked)}")
    bad = [f"{a}: {l}" for a, l in zip(asked, lines) if not l.startswith("ok")]
    if bad:
        raise Fail(f"{name}{f' on {threads} threads' if threads else ''}: {len(bad)} of {len(asked)} "
                   f"failed:\n  " + "\n  ".join(bad[:8]))
    return len(asked)


def mm_check_line(name, m=256, k=256, n=256):
    """The pattern of mm check's line for a variant that passes."""
    return re.compile(rf"^{re.escape(f'{name:<7}')} {m}x{k}x{n}: ok, worst error \S+ at \[\d+\] of {m * n} "
                      rf"\(allowed \S+\)$")


TIME_ROW = re.compile(r"^(\S+) +([0-9.]+) +([0-9.]+|-) +([0-9.]+x|-)$")


def mm_time(t, argv):
    """mm time with argv: (n, threads or None, [(name, ms, gflops, times faster or None)]), or a
    Fail saying what it printed."""
    st, out, err = prog(t, "mm", ["time"] + list(argv), timeout=600)
    lines = out.splitlines()
    try:
        assert st == 0 and lines[0].startswith("n = ")
        n = int(lines[0][4:])
        threads = None
        rest = lines[1:]
        if rest and rest[0].startswith("threads = "):
            threads = int(rest[0][10:])
            rest = rest[1:]
        assert re.match(r"^variant +min ms +GFLOP/s +vs ijk$", rest[0])
        rows = []
        for l in rest[1:]:
            m = TIME_ROW.match(l)
            assert m
            rows.append((m.group(1), float(m.group(2)), None if m.group(3) == "-" else float(m.group(3)),
                         None if m.group(4) == "-" else float(m.group(4)[:-1])))
        return n, threads, rows
    except (AssertionError, IndexError, ValueError):
        raise Fail(f"mm time {' '.join(argv)}: status {st}:\n{out}{err}")


# ---------------------------------------------------------------- the project at each lesson
#
# Internal: ./learn check-timeline gpu builds the project as the site shows it at each lesson
# (harness/timeline.py) and starts a shell there. timeline_boot types commands into it, each
# followed by echo "@@ $?", and checks what each prints and its status: each lesson's commands,
# and for what a later lesson brings, an ordinary usage error, never a crash or a stub.

TIMELINE_FAIL = [r"not written yet", r"Segmentation fault", r"Abort", r"core dumped", r"Bus error",
                 r"AddressSanitizer", r"runtime error:"]


def timeline_run(root):
    return ["/bin/sh"]


def sh_step(command, out=None, status=0, regex=None):
    """One command for the timeline's shell: what it prints (stdout and stderr together; exactly
    out, or regex), then its exit status."""
    body = regex if regex is not None else "".join(re.escape(l) + r"\r?\n" for l in (out or "").splitlines())
    return (f'{command}; echo "@@ $?"', "(?s)^" + body + rf"@@ {status}\r?\n")


VARIANTS = [("ijk", (1, 1)), ("ikj", (1, 2)), ("simd", (1, 3)), ("blocked", (1, 4)), ("threads", (1, 5)),
            ("blas", (1, 5))]


def wb_usage(k):
    lines = ["usage: wb show [-n N] [-s SEED]"]
    if k >= (0, 2):
        lines.append("       wb check [-n N] [-s SEED]")
    if k >= (0, 3):
        lines.append("       wb time [-n N]")
    return "".join(l + "\n" for l in lines)


def mm_usage(k):
    t = " [-t T]" if k >= (1, 5) else ""
    return (f"usage: mm list\n       mm check{t} [name...]\n       mm time [-n N]{t} [name...]\n")


def timeline_boot(lesson_id):
    from harness.core import lesson_key
    k = lesson_key(lesson_id)
    S = sh_step
    steps = [S("./wb show", show_text(1003, 1)),
             S("./wb show -n 2 -s 7", show_text(2, 7)),
             S("./wb show -s 0", "wb: -s 0: xorshift's state 0 never changes, so every number would be the "
                                 "same; a seed is 1 to 4294967295\n", status=2),
             S("./wb show -n 0", "wb: -n wants a whole number from 1 to 268435456, not '0'\n", status=2)]
    if k < (0, 2):
        steps.append(S("./wb check", wb_usage(k), status=2))
    else:
        steps += [S("./wb check", "add: ok, worst error 0 at [0] of 1003 (allowed 0)\n"),
                  S("./wb check -n 5 -s 9", "add: ok, worst error 0 at [0] of 5 (allowed 0)\n")]
    if k < (0, 3):
        steps.append(S("./wb time", wb_usage(k), status=2))
    else:
        steps.append(S("./wb time -n 4096", regex=r"add: n = 4096, \d+ runs, min [0-9.e+-]+ ms, median [0-9.e+-]+ ms, "
                                                  r"(?:[0-9.]+ GB/s|too fast for the clock: try a larger -n)\r?\n"))
    if k < (1, 1):
        return steps
    have = [name for name, at in VARIANTS if k >= at]
    listed = [n for n in have if n != "blas"]
    steps.append(S("./mm list | grep -v blas", "".join(n + "\n" for n in listed)))
    steps.append(S("./mm check",
                   regex="".join(rf"{n:<7} 256x256x256: ok, worst error \S+ at \[\d+\] of 65536 \(allowed \S+\)\r?\n"
                                 for n in listed) + (r"(?:blas    256x256x256: ok[^\n]*\n|mm: blas: [^\n]*\n)"
                                                     if "blas" in have else "")))
    rows = "".join(rf"{n:<8} +[0-9.]+ +[0-9.]+ +(?:[0-9.]+x|-)\r?\n" for n in listed)
    if "blas" in have:
        rows += r"(?:blas +[0-9.]+ +[0-9.]+ +(?:[0-9.]+x|-)\r?\n|mm: blas: [^\n]*\n)"
    head = r"n = 64\r?\n" + (r"threads = 2\r?\n" if k >= (1, 5) else "") + r"variant +min ms +GFLOP/s +vs ijk\r?\n"
    t = " -t 2" if k >= (1, 5) else ""
    steps.append(S(f"./mm time -n 64{t}", regex=head + rows))
    if k < (1, 5):
        steps.append(S("./mm time -n 64 -t 2", mm_usage(k), status=2))
    nxt = next((n for n, at in VARIANTS if k < at), None)
    if nxt:
        steps.append(S(f"./mm time -n 64 {nxt}", f"mm: no variant called '{nxt}' (mm list names them)\n", status=2))
    steps.append(S("./mm time -n 9000", "mm: -n wants a whole number from 1 to 8192, not '9000'\n", status=2))
    return steps
