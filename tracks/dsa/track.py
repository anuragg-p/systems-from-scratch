"""Track dsa: data structures and algorithms, by building the tools that use them.

The project is a set of small tools in C (tools/<name>/, built into bin/<name>) on one
library of data structures (lib/, one ds.h). Each tool is held to the system's own: the same
bytes out as the machine's sort, paste or look, BSD or GNU, with LC_ALL=C.

Shared fixtures (here), for every tool's tests:

    run(t, tool, args=(), input=None, env=None, check=True, timeout=300)
                        bin/<tool> with args, in the project's directory, LC_ALL=C; input is
                        str or bytes for stdin (None: /dev/null). A Result: .out .err .rc.
                        check=True fails on a non-zero exit. t may be a project root instead.
    system(t, argv, input=None, env=None, check=True)
                        the machine's own program (argv[0] from PATH), LC_ALL=C
    sh(t, script, args=(), input=None, check=True)
                        a POSIX shell script (a pipeline of system tools), LC_ALL=C; args
                        are its $0, $1, ...
    same(t, ours, theirs, what)
                        fail, showing the first line that differs, unless ours == theirs
    stats(err)          the DS_STATS=1 lines of stderr: {"table": {"probes": 12, ...}, ...}
    data(t, name)       the path of data/<name>
    gen(t, kind, n, seed=1, name=None)
                        a file of data/gen.py's kind KIND, size n, in the test's scratch
                        directory: its path (a list of paths for a kind of several files)
    write(t, name, data)
                        a file in the scratch directory; its path
    have(prog)          the path of a system program, or None
    fixtures(name)      the fixtures file of one tool, tests/tools/<name>.py

Per tool, tests/tools/<name>.py (loaded by this file, in name order; `T` in it is this module)
may define:

    PROGRAMS = {"freq": "01.01"}   the programs it adds to bin/, and the lesson each comes with
    FILES_FROM, HIDDEN, SOURCES, STUBS, UPSTREAM
                        merged into this file's own (a path named twice is an error)
    timeline_steps(k)   check-timeline steps for the project at lesson k (a (module, lesson)
                        tuple), as [sh_step(...), ...]: commands typed into one shell
    timeline_after(root, k)
                        checks after that shell is gone: raise Fail, or return a short note
    and any fixtures its own tests use: fixtures("freq").pipeline(t, path)

Tests are internal. A lesson's test runs the tools it is about, so with that lesson's code cut
out it fails at the stub: "<tool>: NN.LL: <what> not written yet", exit status 3.
"""

import importlib.util
import os
import re
import shutil
import subprocess
import sys

from harness.core import Fail, lesson_key

TITLE = "Data structures and algorithms, by building the tools that use them"
KIND = "algorithms"
SUMMARY = ("Ten Unix tools in C on a library of structures you write, each written the obvious way, "
           "run until it stops finishing, then fixed and measured against the real one.")

# What this track is held to (see harness/web/views.py, upstreams()). No code is taken from
# either: the tools are ours, and are checked against whichever the machine has.
UPSTREAM = [
    {"name": "GNU coreutils",
     "url": "https://www.gnu.org/software/coreutils/",
     "licence": "GPL-3.0-or-later",
     "owes": "No code. Our sort and paste print the same bytes as theirs, the Linux ones, and freq "
             "the same counts as their tr, sort and uniq.",
     "derived": False},
    {"name": "FreeBSD's utilities",
     "url": "https://github.com/freebsd/freebsd-src/tree/main/usr.bin",
     "licence": "BSD-2-Clause",
     "owes": "No code. The same checks pass against the BSD sort, paste, tr, uniq and look that "
             "macOS ships.",
     "derived": False},
]

# Files that may hold "@build NN.LL" regions (harness/workspace.py), and what a cut region
# becomes: ds_todo() (@internal in lib/util.c) prints "<tool>: NN.LL: <what> not written
# yet" and exits 3.
SOURCES = ["lib/*.c", "lib/*.h", "tools/*/*.c", "tools/*/*.h"]
STUBS = {".c": 'ds_todo("{id}", "{title}");'}
# Not for learners: the notes for the lesson writers, and what make builds.
HIDDEN = ["NOTES.md", "bin/*"]
# When each file comes into the project the site shows (harness/timeline.py). A file with
# @build regions comes with its first region; every other file is named here, or in its
# tool's tests/tools/<name>.py.
FILES_FROM = {
    "Makefile": "00.01",
    "lib/ds.h": "00.01",
    "lib/util.c": "00.01",
    "data/book.txt": "00.01",
    "bench/grow.py": "00.02",
    "data/gen.py": "00.02",
}

# The inputs that ship with the track (NOTICE, and NOTES.md, say where each came from).
DATA = {
    "data/book.txt": "The Adventures of Sherlock Holmes, Arthur Conan Doyle (1892); public domain. "
                     "Project Gutenberg eBook #1661 without its header, footer and licence, in ASCII.",
}


def build(t):
    t.run(["make", "-s"])


# ---------------------------------------------------------------- run it, and the benchmark
#
# The track contract's optional hooks, all run with cwd=root: prepare(root) builds the tree,
# run_argv(root, args) starts it, bench(root) runs the growth harness.

def prepare(root):
    return ["make", "-s"]


def run_argv(root, args=()):
    """./learn run dsa -- TOOL ARGS runs bin/TOOL with ARGS in the project's directory
    (./learn run dsa --at 01.02 -- freq data/book.txt); with nothing after --, a shell there."""
    bindir = os.path.join(root, "bin")
    tools = sorted(os.listdir(bindir)) if os.path.isdir(bindir) else []
    if not args:
        hint = f"The tools are in bin/ ({', '.join(tools)}); exit leaves this shell."
        return ["/bin/sh", "-c", 'echo "$0"; exec "${SHELL:-/bin/sh}"', hint]
    tool = args[0]
    if tool.startswith("bin/"):
        tool = tool[4:]
    if tool not in tools:
        msg = f"no tool {args[0]} at this lesson; the tools here: {', '.join(tools) or 'none'}"
        return [sys.executable, "-c", "import sys; sys.exit(sys.argv[1])", msg]
    return [os.path.join(bindir, tool)] + list(args[1:])


def bench(root):
    """The growth harness; ./learn bench's other arguments are its own and the command's."""
    return [sys.executable, "bench/grow.py"]


# ---------------------------------------------------------------- ./learn verify

def verify_tools():
    """What replaying a lesson needs: the compiler and make, and the system's tools the lessons
    compare with."""
    return {name: shutil.which(name) for name in ("cc", "make", "sort", "tr", "uniq", "paste")}


# ---------------------------------------------------------------- the shared fixtures

class Result:
    def __init__(self, argv, r):
        self.argv = argv
        self.raw = r.stdout
        self.out = r.stdout.decode("utf-8", "surrogateescape")
        self.err = r.stderr.decode("utf-8", "surrogateescape")
        self.rc = r.returncode

    def lines(self):
        return self.out.splitlines()

    def __repr__(self):
        return (f"$ {' '.join(self.argv)}\nrc={self.rc}\n--- stdout\n{self.out[-1500:]}"
                f"\n--- stderr\n{self.err[-1500:]}")


def _root(t):
    return t if isinstance(t, str) else t.root


def _env(extra=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("DS_")}
    env["LC_ALL"] = "C"
    env.update(extra or {})
    return env


def _exec(argv, input, env, check, cwd, timeout):
    if isinstance(input, str):
        input = input.encode("utf-8", "surrogateescape")
    try:
        r = subprocess.run(argv, input=input, stdin=None if input is not None else subprocess.DEVNULL,
                           capture_output=True, env=env, cwd=cwd, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise Fail(f"{' '.join(argv)} did not finish in {timeout}s")
    except OSError as e:
        raise Fail(f"cannot run {argv[0]}: {e}")
    res = Result(argv, r)
    if check and res.rc != 0:
        raise Fail(f"exit status {res.rc}:\n{res}")
    return res


def run(t, tool, args=(), input=None, env=None, check=True, timeout=300):
    """bin/<tool> with args, in the project's directory."""
    root = _root(t)
    return _exec([os.path.join(root, "bin", tool)] + [str(a) for a in args], input, _env(env), check,
                 root, timeout)


def system(t, argv, input=None, env=None, check=True, timeout=300):
    """The machine's own program: argv[0] from PATH, never bin/."""
    exe = shutil.which(argv[0])
    if exe is None:
        raise Fail(f"no {argv[0]} on this machine")
    return _exec([exe] + [str(a) for a in argv[1:]], input, _env(env), check, _root(t), timeout)


def sh(t, script, args=(), input=None, check=True, timeout=300):
    """A shell script of system tools: sh -c script args..."""
    return _exec(["/bin/sh", "-c", script] + [str(a) for a in args], input, _env(), check, _root(t), timeout)


def same(t, ours, theirs, what="the output"):
    """Fail unless ours == theirs, with the first line that differs."""
    if ours == theirs:
        return
    a, b = ours.split("\n"), theirs.split("\n")
    for i in range(max(len(a), len(b))):
        x = a[i] if i < len(a) else "<nothing>"
        y = b[i] if i < len(b) else "<nothing>"
        if x != y:
            raise Fail(f"{what}: ours and the system's differ at line {i + 1} "
                       f"({len(a) - 1} lines against {len(b) - 1}):\n  ours:   {x!r}\n  system: {y!r}")
    raise Fail(f"{what}: ours and the system's differ")


STATS = re.compile(r"^stats: ([^:]+): (.*)$", re.M)


def stats(err):
    """The DS_STATS=1 lines: {"structure": {"count": n, ...}}."""
    out = {}
    for m in STATS.finditer(err):
        d = out.setdefault(m.group(1), {})
        for part in m.group(2).split(", "):
            name, n = part.rsplit(" ", 1)
            d[name] = int(n)
    if not out:
        raise Fail(f"no stats lines (DS_STATS=1) in:\n{err[-1500:]}")
    return out


def data(t, name):
    return os.path.join(_root(t), "data", name)


_gens = {}


def _gen_module(root):
    path = os.path.join(root, "data", "gen.py")
    if path not in _gens:
        spec = importlib.util.spec_from_file_location(f"dsa_gen_{len(_gens)}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _gens[path] = mod
    return _gens[path]


def gen(t, kind, n, seed=1, name=None):
    """A generated input in the test's scratch directory: its path (several: a list)."""
    made = _gen_module(_root(t)).make(kind, n, seed)
    name = name or f"{kind}-{n}-{seed}"
    if isinstance(made, (list, tuple)):
        return [write(t, f"{name}.{i + 1}", d) for i, d in enumerate(made)]
    return write(t, name, made)


def write(t, name, content):
    path = os.path.join(t.tmp, name)
    with open(path, "wb") as f:
        f.write(content.encode("utf-8", "surrogateescape") if isinstance(content, str) else content)
    return path


def have(prog):
    return shutil.which(prog)


# ---------------------------------------------------------------- the project at each lesson
#
# Internal: ./learn check-timeline dsa builds the project as the site shows it at each lesson
# (harness/timeline.py) and starts a shell in it (timeline_run). Each tool's timeline_steps(k)
# types commands into that shell: what the tool can do at lesson k, and an ordinary error for
# what a later lesson brings. Then each tool's timeline_after(root, k) checks its output against
# the system's. The shell reads its commands from a pipe; no command may read standard input
# unless the step gives it some.

TIMELINE_FAIL = [r"not written yet", r"Segmentation fault", r"Abort", r"core dumped", r"Bus error",
                 r"Illegal instruction", r"AddressSanitizer"]


def timeline_run(root):
    return ["/bin/sh"]


def sh_step(command, out=None, status=0, regex=None):
    """One command for the timeline's shell: (what to type, what must come back). out is the
    exact text it prints (stdout and stderr together), or regex a pattern for it; then the
    exit status must be status."""
    body = regex if regex is not None else "".join(re.escape(l) + r"\r?\n" for l in (out or "").splitlines())
    return (f'{command}; echo "@@ $?"', "(?s)^" + (body if out or regex else "") + rf"@@ {status}\r?\n")


def _key(k):
    return lesson_key(k) if isinstance(k, str) else k


def programs_at(k):
    """The programs bin/ holds at lesson k: every tool's PROGRAMS whose lesson is reached."""
    k = _key(k)
    return sorted(p for m in TOOL_FIXTURES.values() for p, lid in getattr(m, "PROGRAMS", {}).items()
                  if lesson_key(lid) <= k)


def timeline_boot(lesson_id):
    k = lesson_key(lesson_id)
    steps = [sh_step("ls bin", "".join(p + "\n" for p in programs_at(k)))]
    for m in TOOL_FIXTURES.values():
        steps += list(getattr(m, "timeline_steps", lambda k: [])(k))
    return steps


def timeline_after(root, lesson_id):
    k = lesson_key(lesson_id)
    notes = []
    for m in TOOL_FIXTURES.values():
        after = getattr(m, "timeline_after", None)
        note = after(root, k) if after else None
        if note:
            notes.append(note)
    return "; ".join(notes)


# ---------------------------------------------------------------- each tool's own file

TOOLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "tools")


def _load_tools():
    out = {}
    names = sorted(f[:-3] for f in os.listdir(TOOLS_DIR) if f.endswith(".py") and not f.startswith("_"))
    for name in names:
        spec = importlib.util.spec_from_file_location(f"{__name__}_tool_{name}", os.path.join(TOOLS_DIR, name + ".py"))
        mod = importlib.util.module_from_spec(spec)
        mod.T = sys.modules[__name__]
        spec.loader.exec_module(mod)
        out[name] = mod
    return out


def fixtures(name):
    """The fixtures file of one tool: tests/tools/<name>.py."""
    try:
        return TOOL_FIXTURES[name]
    except KeyError:
        raise Fail(f"no tests/tools/{name}.py")


TOOL_FIXTURES = _load_tools()
for _name, _m in TOOL_FIXTURES.items():
    for _path, _lid in getattr(_m, "FILES_FROM", {}).items():
        if _path in FILES_FROM:
            raise Fail(f"tests/tools/{_name}.py: FILES_FROM names {_path}, which is named already")
        FILES_FROM[_path] = _lid
    HIDDEN += [p for p in getattr(_m, "HIDDEN", []) if p not in HIDDEN]
    SOURCES += [p for p in getattr(_m, "SOURCES", []) if p not in SOURCES]
    for _ext, _stub in getattr(_m, "STUBS", {}).items():
        STUBS.setdefault(_ext, _stub)
    UPSTREAM += list(getattr(_m, "UPSTREAM", []))
