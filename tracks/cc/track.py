"""Track cc: a C compiler for RISC-V, chibicc's front end rebuilt lesson by lesson (UPSTREAM).

The compiler is one program, ./cc [--tokens] [--tree] [-o out.s] FILE (make builds it with the
host's C compiler). It reads a file and writes RISC-V assembly, and nothing else: the RISC-V
toolchain's as and ld make a program of it with the runtime in rt/, and QEMU runs that on its
bare virt machine (no firmware, no kernel), where what main returns becomes QEMU's exit status.
ccrun does those steps for one file; same does them with gcc for the same machine as well, and
compares. Until module 03 the input is one expression and the program returns its value.

Fixtures the lesson tests use (t is the test's context; src is the text of a source file):

    compile(t, src, *flags)   ./cc on src, written to a file of the test's scratch directory and
                              named there without a directory (so an error's first line is
                              "t1.c:1: ..."): (status, stdout, stderr)
    asm(t, src, *flags)       its assembly (stdout); fails the test if ./cc failed
    run(t, src)               compile, assemble, link with rt/ and run in QEMU, all in the
                              scratch directory: (status, output). Fails if ./cc fails or the
                              program does not stop within 10 seconds
    gcc_run(t, src)           the same with gcc (wrapped in a main, as same does)
    same(t, src)              run() and gcc_run(); fails on any difference; returns the status
    value(t, expr, want)      expr must give want: same() on it (status want & 0xff, as gcc's),
                              and ./cc's program for "(expr) == (want)" must return 1, so all
                              64 bits are checked, not just the 8 a status carries
    error(t, src)             src must be a compile error (status 1, two lines on stderr): an
                              Error with .msg, .line, .col (of the caret, from 1, a tab counted
                              as one), .text (the source line shown) and .stderr
    tokens(t, src)            ./cc --tokens, parsed: [Tok(line, col, kind, text, value)], value
                              an int for num (its value) and str (its decoded length), else None
    tree(t, src)              ./cc --tree, parsed into nested lists: "2*3+4" is
                              ["+", ["*", 2, 3], 4]; a number is an int
    sexp(tree)                that, written short: "(+ (* 2 3) 4)"
    script(t, name, *args, cwd=None, env=None)
                              one of the project's scripts (ccrun, same), from cwd (default the
                              scratch directory), stdin /dev/null: (status, stdout, stderr)
    tools()                   the RISC-V toolchain and QEMU: {"prefix", "gcc", "as", "ld",
                              "qemu"}; fails with one line saying what to install
    libc_problems(root)       the compiler's sources against the headers and C functions it may
                              use (LIBC_HEADERS, LIBC_FUNCTIONS): [problem], [] when all is well
    warnings(t)               the sources compiled with -Werror and the Makefile's flags, by the
                              host's compiler: its messages, "" when there are none

CC_SANITIZE=1 in the environment makes compile() (and so every fixture above that compiles) use
./cc built with AddressSanitizer and UndefinedBehaviorSanitizer, once per run, outside the track;
a sanitizer's report fails the test. The scripts still run the plain ./cc.

Tests are internal. A lesson's test runs the compiler, so with that lesson's code cut out it
fails at the stub: "cc: NN.LL: <what> not written yet", exit status 3.

check-timeline builds the project at each lesson and types commands into a shell in it
(timeline_boot): the lesson's sample, try.c, compiled and run, its tokens and its tree, and the
sample files timeline_run() writes, each checked for exactly what it prints and its status.
"""

import os
import re
import shutil
import subprocess
import tempfile
import threading

try:
    from harness.core import Fail
except ImportError:          # run as a program (tests/fuzz_expr.py loads this file too)
    class Fail(Exception):
        pass

TITLE = "A C compiler for RISC-V"
KIND = "compiler"
SUMMARY = ("A compiler for C, written in C, that is a whole compiler at every lesson: from one "
           "number to expressions, held to gcc's answers on a bare RISC-V machine in QEMU.")

# The code this track is built on (see harness/web/views.py, upstreams()): its front end is
# derived from chibicc, so every lesson page says so. LICENSE is chibicc's, whole, and comes
# with the project's files from the first lesson (FILES_FROM).
UPSTREAM = {
    "name": "chibicc",
    "url": "https://github.com/rui314/chibicc",
    "licence": "MIT",
    "copyright": "Copyright (c) 2019 Rui Ueyama",
    "owes": "The front end (the scanner, the parser and later the preprocessor and the types) "
            "is chibicc's, with its names and its structure; the RISC-V code generator and the "
            "runtime are this course's.",
    "derived": True,
    "licence_file": "LICENSE",
    "chip": "based on chibicc",
}

# Files that may hold "@build NN.LL" regions (see harness/workspace.py), and what replaces a
# region's code when a learner's workspace cuts it: todo() (@internal in main.c) prints
# "cc: NN.LL: <title> not written yet" and exits 3; in the scripts (no extension), the same
# from the shell.
SOURCES = ["*.c", "*.h", "ccrun", "same"]
STUBS = {
    ".c": 'todo("{id}", "{title}");',
    "": 'echo "cc: {id}: {title} not written yet" >&2; exit 3',
}
# Not for learners: notes for the lesson writers, and what make builds (macOS keeps the debug
# symbols of ./cc in cc.dSYM/). build/ (what ccrun and same make) is never part of a project.
HIDDEN = ["NOTES.md", "cc", "cc.dSYM/*"]
# When each file comes into the project the site shows (see harness/timeline.py): main.c comes
# with its first region (00.01), ccrun (00.02), same (00.03), tokenize.c (01.01), parse.c
# (02.01) and codegen.c (02.03) with theirs. The files without regions are named here. What a
# later lesson adds to a file outside its regions is marked "@from NN.LL" in the file itself.
FILES_FROM = {
    "LICENSE": "00.01",          # chibicc's licence goes with every copy of the project
    "Makefile": "00.01",
    "try.c": "00.01",            # the sample ./learn run compiles; it changes by lesson
    "rt/start.S": "00.02",       # the runtime: where the machine starts, and where things sit
    "rt/link.ld": "00.02",
    "cc.h": "01.01",             # with the second file of C, what the files share
}

# What the compiler's own source may use of the C library: it has to compile itself on a bare
# machine at the end of the track, against a small C library of the course's own.
LIBC_HEADERS = {"stdio.h", "stdlib.h", "string.h", "ctype.h", "stdarg.h", "stdbool.h"}
LIBC_FUNCTIONS = {
    "fopen", "fclose", "fread", "fprintf", "vfprintf", "printf", "fputc",     # stdio.h
    "calloc", "realloc", "exit", "strtoul",                                    # stdlib.h
    "strlen", "strcmp", "strncmp", "memcmp", "memcpy", "strchr",               # string.h
    "isdigit", "isalpha", "isalnum", "isspace", "isxdigit",                    # ctype.h
    "va_start", "va_end", "va_arg", "va_copy",                                 # stdarg.h
}


def build(t):
    t.run(["make", "-s"])


# ---------------------------------------------------------------- run it
#
# The track contract's optional hooks: prepare(root) returns the command that builds the tree,
# run_argv(root) the command that runs it. Both run with cwd=root: the project as it stands at a
# lesson (./learn run cc --at NN.LL), or the finished track.

def prepare(root):
    return ["make", "-s"]


def run_argv(root, args=()):
    """The lesson's sample, try.c: ./ccrun try.c (./cc try.c before ccrun exists at 00.02), and
    ./cc --tree try.c at 02.01 and 02.02, where the parser is there but the code generator is
    not. With args (./learn run cc -- ...): ./cc with them when the first is an option
    (--tokens f.c), one of the scripts when the first names it (same f.c), else ccrun on them."""
    def has(f):
        return os.path.exists(os.path.join(root, f))
    args = list(args)
    if args:
        name = args[0][2:] if args[0].startswith("./") else args[0]
        if name in ("cc", "ccrun", "same"):
            return ["./" + name] + args[1:]
        if args[0].startswith("-"):
            return ["./cc"] + args
        return (["./ccrun"] if has("ccrun") else ["./cc"]) + args
    if has("parse.c") and not has("codegen.c"):
        return ["./cc", "--tree", "try.c"]
    return ["./ccrun" if has("ccrun") else "./cc", "try.c"]


# ---------------------------------------------------------------- the tools

PREFIXES = ("riscv64-elf-", "riscv64-unknown-elf-", "riscv64-linux-gnu-")
INSTALL = ("install the riscv64 gcc toolchain and qemu-system-riscv64, as the xv6 track does "
           "(macOS: brew install riscv64-elf-gcc qemu; Debian: apt install gcc-riscv64-unknown-elf "
           "qemu-system-misc)")
AS_FLAGS = ["-march=rv64im", "-mabi=lp64"]
# gcc as same runs it. -mcmodel=medany and -fno-pie: the program sits at 0x80000000, which the
# default code model (addresses within 2 GiB of 0) cannot reach, and a position-independent one
# would want a GOT; neither matters until there are global variables, both are right then.
GCC_FLAGS = ["-O0", "-march=rv64im", "-mabi=lp64", "-mcmodel=medany", "-fno-pie", "-ffreestanding",
             "-nostdlib", "-fno-builtin", "-mno-relax"]
QEMU = ["qemu-system-riscv64", "-machine", "virt", "-bios", "none", "-display", "none",
        "-monitor", "none", "-serial", "stdio", "-kernel"]
RUN_SECONDS = 10

_tools = None


def tools():
    """The RISC-V tools: the first prefix with gcc, as and ld, and QEMU. Fails in one line."""
    global _tools
    if _tools is None:
        prefix = next((p for p in PREFIXES if all(shutil.which(p + x) for x in ("gcc", "as", "ld"))), None)
        qemu = shutil.which("qemu-system-riscv64")
        missing = ([] if prefix else ["riscv64 gcc, as and ld"]) + ([] if qemu else ["qemu-system-riscv64"])
        if missing:
            raise Fail(f"no {' and no '.join(missing)}: {INSTALL}")
        _tools = {"prefix": prefix, "gcc": prefix + "gcc", "as": prefix + "as", "ld": prefix + "ld",
                  "qemu": qemu}
    return _tools


# ---------------------------------------------------------------- the compiler under test

_san_lock = threading.Lock()
_san = {}


def cc_path(t):
    """./cc of the tree under test, or with CC_SANITIZE=1 the same sources built with ASan and
    UBSan into a directory of its own (once per tree per run)."""
    if not os.environ.get("CC_SANITIZE"):
        return os.path.join(t.root, "cc")
    with _san_lock:
        if t.root not in _san:
            out = tempfile.mkdtemp(prefix="cc-sanitize-")
            exe = os.path.join(out, "cc")
            srcs = sorted(f for f in os.listdir(t.root) if f.endswith(".c") and f != "try.c")
            r = subprocess.run([os.environ.get("HOSTCC", "cc"), "-std=c11", "-g", "-fno-omit-frame-pointer",
                                "-fsanitize=address,undefined", "-fno-sanitize-recover=all", "-o", exe] + srcs,
                               cwd=t.root, capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                raise Fail(f"the sanitizer build of ./cc failed:\n{r.stderr[-2000:]}")
            _san[t.root] = exe
        return _san[t.root]


SANITIZER = re.compile(r"AddressSanitizer|UndefinedBehaviorSanitizer|runtime error:|LeakSanitizer")


def _write(t, src, ext=".c"):
    t._cc_files = getattr(t, "_cc_files", 0) + 1
    name = f"t{t._cc_files}{ext}"
    with open(os.path.join(t.tmp, name), "wb") as f:
        f.write(src.encode("latin-1") if isinstance(src, str) else src)
    return name


def _text(b):
    return b.decode("latin-1")


def compile(t, src, *flags):
    """./cc FLAGS FILE, FILE holding src: (status, stdout, stderr)."""
    name = _write(t, src)
    env = dict(os.environ)
    env.setdefault("ASAN_OPTIONS", "detect_leaks=0")    # the compiler frees nothing, as chibicc
    try:
        r = subprocess.run([cc_path(t)] + list(flags) + [name], cwd=t.tmp, capture_output=True,
                           timeout=60, env=env)
    except subprocess.TimeoutExpired:
        raise Fail(f"./cc did not stop within 60 s on {src!r}")
    err = _text(r.stderr)
    if SANITIZER.search(err):
        raise Fail(f"./cc on {src!r}: a sanitizer report:\n{err[-3000:]}")
    return r.returncode, _text(r.stdout), err


def asm(t, src, *flags):
    st, out, err = compile(t, src, *flags)
    if st != 0:
        raise Fail(f"./cc failed (status {st}) on {src!r}:\n{err}")
    return out


def _start_o(t):
    """rt/start.S of the tree under test, assembled once per test."""
    path = os.path.join(t.tmp, "start.o")
    if not os.path.exists(path):
        _tool(t, [tools()["as"]] + AS_FLAGS + ["-o", path, os.path.join(t.root, "rt", "start.S")])
    return path


def _tool(t, argv):
    r = subprocess.run(argv, cwd=t.tmp, capture_output=True, timeout=60)
    if r.returncode != 0:
        raise Fail(f"{os.path.basename(argv[0])} failed (status {r.returncode}): {' '.join(argv)}\n"
                   f"{_text(r.stdout)}{_text(r.stderr)}")
    return r


def _qemu(t, elf, stdin=b""):
    try:
        r = subprocess.run([tools()["qemu"]] + QEMU[1:] + [elf], cwd=t.tmp, input=stdin,
                           capture_output=True, timeout=RUN_SECONDS)
    except subprocess.TimeoutExpired:
        raise Fail(f"the program did not stop within {RUN_SECONDS} s ({elf})")
    return r.returncode, _text(r.stdout)


def _link_run(t, obj, base):
    elf = os.path.join(t.tmp, base + ".elf")
    _tool(t, [tools()["ld"], "-T", os.path.join(t.root, "rt", "link.ld"), "-o", elf, _start_o(t), obj])
    return _qemu(t, elf)


def run(t, src):
    """src compiled by ./cc and run on QEMU: (status, output)."""
    tools()
    st, out, err = compile(t, src, "-o", f"p{getattr(t, '_cc_files', 0) + 1}.s")
    if st != 0:
        raise Fail(f"./cc failed (status {st}) on {src!r}:\n{err}")
    base = f"p{t._cc_files}"
    obj = os.path.join(t.tmp, base + ".o")
    _tool(t, [tools()["as"]] + AS_FLAGS + ["-o", obj, base + ".s"])
    return _link_run(t, obj, base)


def gcc_source(src):
    """What same gives gcc: before module 03 the input is an expression, so it goes in a main."""
    return "int main(void) { return " + src + "\n; }\n"


def gcc_run(t, src):
    """src compiled by gcc for the same machine, linked with the same runtime, run: (status,
    output)."""
    name = _write(t, gcc_source(src))
    base = "g" + name[:-2]
    obj = os.path.join(t.tmp, base + ".o")
    _tool(t, [tools()["gcc"]] + GCC_FLAGS + ["-c", "-o", obj, name])
    return _link_run(t, obj, base)


def same(t, src):
    """src through ./cc and through gcc: the same status and output, or the test fails."""
    ours = run(t, src)
    theirs = gcc_run(t, src)
    if ours != theirs:
        raise Fail(f"{src!r}: ours: status {ours[0]}, output {ours[1]!r}; "
                   f"gcc: status {theirs[0]}, output {theirs[1]!r}")
    return ours[0]


def c_int(n):
    """n written as an expression that needs no unary minus: (0 - 5)."""
    return f"(0 - {-n})" if n < 0 else str(n)


def value(t, expr, want):
    """expr gives want: the same status as gcc's, want's low 8 bits, and all 64 bits right."""
    st = same(t, expr)
    if st != want & 0xff:
        raise Fail(f"{expr!r}: status {st} (gcc agrees), but {want} should give {want & 0xff}")
    st, _ = run(t, f"({expr}) == ({c_int(want)})")
    if st != 1:
        raise Fail(f"{expr!r}: its low 8 bits are right, but ({expr}) == ({want}) is {st}, not 1")


class Error:
    """A compile error as ./cc prints it: the message, the line, the caret's column (from 1,
    counting a tab as one), the source line shown, and all of stderr."""

    def __init__(self, msg, line, col, text, stderr):
        self.msg, self.line, self.col, self.text, self.stderr = msg, line, col, text, stderr

    def __repr__(self):
        return f"Error({self.msg!r}, line {self.line}, col {self.col})"


def error(t, src, *flags):
    """src must not compile: status 1, and the two lines of an error on stderr."""
    st, out, err = compile(t, src, *flags)
    if st != 1:
        raise Fail(f"{src!r} should be a compile error (status 1), but ./cc exited {st}:\n{out}{err}")
    lines = err.split("\n")
    m = re.match(r"^(\S+?):(\d+): (.*)$", lines[0])
    if not m or len(lines) < 2 or "^ " not in lines[1]:
        raise Fail(f"{src!r}: not an error in two lines (FILE:LINE: text, then a caret):\n{err}")
    prefix = len(m.group(1)) + len(m.group(2)) + 3
    caret = lines[1].index("^ ")
    under = lines[1][prefix:caret]
    if lines[1][:prefix].strip() or (under.strip(" \t")):
        raise Fail(f"{src!r}: the caret's line should be spaces and tabs, then '^ ':\n{err}")
    return Error(lines[1][caret + 2:], int(m.group(2)), len(under) + 1, m.group(3), err)


class Tok:
    def __init__(self, line, col, kind, text, value):
        self.line, self.col, self.kind, self.text, self.value = line, col, kind, text, value

    def __eq__(self, other):
        return isinstance(other, Tok) and vars(self) == vars(other)

    def __repr__(self):
        """As --tokens prints it: "1:3 punct +", "1:5 num 20 20", "1:11 eof"."""
        text = f" {self.text}" if self.text else ""
        v = "" if self.value is None else f" {self.value}"
        return f"{self.line}:{self.col} {self.kind}{text}{v}"


def tokens(t, src):
    """./cc --tokens on src, parsed: one Tok a line."""
    out = asm(t, src, "--tokens")
    toks = []
    for line in out.split("\n")[:-1]:
        m = re.match(r"^(\d+):(\d+) (\w+)(?: (.*))?$", line)
        if not m:
            raise Fail(f"--tokens printed a line that is not LINE:COL KIND TEXT: {line!r}")
        kind, rest, value = m.group(3), m.group(4) or "", None
        if kind in ("num", "str"):
            rest, v = rest.rsplit(" ", 1)
            value = int(v)
        toks.append(Tok(int(m.group(1)), int(m.group(2)), kind, rest, value))
    return toks


def tree(t, src):
    """./cc --tree on src, parsed into nested lists: [op, child, ...], a number an int."""
    out = asm(t, src, "--tree")
    lines = out.split("\n")[:-1]
    pos = 0

    def node(depth):
        nonlocal pos
        line = lines[pos]
        ind = len(line) - len(line.lstrip(" "))
        if ind != depth * 2:
            raise Fail(f"--tree: {line!r} is indented {ind}, not {depth * 2}:\n{out}")
        pos += 1
        label = line.strip()
        if label.startswith("num "):
            return int(label[4:])
        kids = [label]
        while pos < len(lines) and len(lines[pos]) - len(lines[pos].lstrip(" ")) > depth * 2:
            kids.append(node(depth + 1))
        return kids

    got = node(0)
    if pos != len(lines):
        raise Fail(f"--tree printed more than one tree:\n{out}")
    return got


def sexp(tr):
    """A tree from tree() written short: ["+", ["*", 2, 3], 4] is "(+ (* 2 3) 4)"."""
    if isinstance(tr, list):
        return "(" + " ".join(sexp(x) for x in tr) + ")"
    return str(tr)


def script(t, name, *args, cwd=None, env=None):
    """./ccrun or ./same of the tree under test, run from cwd (the scratch directory by
    default) with no input: (status, stdout, stderr)."""
    tools()
    try:
        r = subprocess.run([os.path.join(t.root, name)] + list(args), cwd=cwd or t.tmp,
                           capture_output=True, stdin=subprocess.DEVNULL, env=env, timeout=120)
    except subprocess.TimeoutExpired:
        raise Fail(f"{name} {' '.join(args)} did not finish within 120 s")
    return r.returncode, _text(r.stdout), _text(r.stderr)


def write(t, name, text):
    """A file in the scratch directory; its path."""
    path = os.path.join(t.tmp, name)
    with open(path, "wb") as f:
        f.write(text.encode("latin-1") if isinstance(text, str) else text)
    return path


class Scratch:
    """What the fixtures need of a test's t, for work done on another thread: the same tree
    under test, and a scratch directory of its own (inside t's)."""

    def __init__(self, root, tmp):
        self.root, self.tmp = root, tmp
        os.makedirs(tmp, exist_ok=True)

    def check(self, cond, message):
        if not cond:
            raise Fail(message)


def parallel(t, fn, items, jobs=None):
    """fn(ctx, item) for every item, on jobs threads (the CPUs, at most 8), each thread with a
    Scratch of its own. Fails naming every item that failed (the first ten shown)."""
    import queue
    from concurrent.futures import ThreadPoolExecutor
    jobs = jobs or min(8, os.cpu_count() or 1)
    free = queue.Queue()
    for i in range(jobs):
        free.put(Scratch(t.root, os.path.join(t.tmp, f"w{i}")))

    def work(item):
        ctx = free.get()
        try:
            fn(ctx, item)
            return None
        except Fail as e:
            return f"{item!r}: {e}"
        finally:
            free.put(ctx)

    tools()
    with ThreadPoolExecutor(jobs) as pool:
        bad = [r for r in pool.map(work, items) if r]
    if bad:
        raise Fail(f"{len(bad)} of {len(items)} failed:\n" + "\n".join(bad[:10]))


# ---------------------------------------------------------------- the compiler's own source

_STRIP = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'', re.S)
C_WORDS = {"if", "for", "while", "switch", "return", "sizeof", "do", "else", "case"}


def compiler_sources(root):
    """The compiler's own C files: every .c and .h at the top of the project but the sample."""
    return sorted(f for f in os.listdir(root) if f.endswith((".c", ".h")) and f != "try.c")


def libc_problems(root):
    """What the compiler's source uses of the C library beyond LIBC_HEADERS and LIBC_FUNCTIONS:
    every #include, and every name called that the sources do not define themselves."""
    problems, defined, called = [], set(), {}
    for f in compiler_sources(root):
        with open(os.path.join(root, f), encoding="latin-1") as fh:
            text = _STRIP.sub(lambda m: '""' if m.group(0)[0] == '"' else " ", fh.read())
        for n, line in enumerate(text.split("\n"), 1):
            inc = re.match(r'\s*#\s*include\s*([<"])([^>"]*)', line)
            if inc:
                if inc.group(1) == "<" and inc.group(2) not in LIBC_HEADERS:
                    problems.append(f"{f}:{n}: #include <{inc.group(2)}>: not one of {', '.join(sorted(LIBC_HEADERS))}")
                continue
            d = re.match(r"\s*#\s*define\s+(\w+)", line)
            if d:
                defined.add(d.group(1))
                continue
            if line[:1] not in ("", " ", "\t", "#", "}"):
                m = re.search(r"([A-Za-z_]\w*)\s*\(", line)
                if m:
                    defined.add(m.group(1))
            for name in re.findall(r"\b([A-Za-z_]\w*)\s*\(", line):
                called.setdefault(name, f"{f}:{n}")
    for name, where in sorted(called.items()):
        if name not in defined and name not in C_WORDS and name not in LIBC_FUNCTIONS:
            problems.append(f"{where}: calls {name}, which is not in the C library the compiler may use")
    return problems


def warnings(t):
    """The compiler's sources compiled by the host's compiler with the Makefile's flags and
    -Werror, into nothing: what it says ("" when it says nothing)."""
    srcs = [f for f in compiler_sources(t.root) if f.endswith(".c")]
    r = subprocess.run([os.environ.get("HOSTCC", "cc"), "-std=c11", "-Wall", "-Wextra", "-pedantic",
                        "-Werror", "-fsyntax-only"] + srcs, cwd=t.root, capture_output=True, text=True,
                       timeout=120)
    return (r.stdout + r.stderr).strip()


# ---------------------------------------------------------------- the project at each lesson
#
# Internal: ./learn check-timeline cc builds the project as the site shows it at each lesson
# (harness/timeline.py), writes a few sample files into it (timeline_run) and starts a shell
# there. timeline_boot types commands into the shell, each followed by echo "@@ $?", and checks
# exactly what it prints and its status: try.c compiled, run and held to gcc as far as the
# lesson's code goes; its tokens and its tree once those exist; and an ordinary error, never a
# crash or a stub, for what a later lesson brings.

TIMELINE_FAIL = [r"not written yet", r"Segmentation fault", r"Abort", r"core dumped", r"Bus error",
                 r"AddressSanitizer", r"runtime error:"]

TIMELINE_FILES = {
    "two.c": "4 2\n",
    "mul.c": "1 * 2\n",
    "punct.c": "1 >>= 2 -> 3\n",
    "ident.c": "return x1 _y\n",
    "lit.c": "/* a comment */ \"a\\tb\" '\\n' 0x1F 017 0b101 // the end\n",
    "end.c": "1 +\n\t2 +\n",
    "ops.c": "6 % 4 << 2 | 1\n",
    "cmp.c": "-3 < 2 == !0\n",
    "deep.c": "1 - (2 - (3 - (4 - (5 - (6 - 7)))))\n",
}


def timeline_run(root):
    for name, text in TIMELINE_FILES.items():
        with open(os.path.join(root, name), "w") as f:
            f.write(text)
    return ["/bin/sh"]


def sh_step(command, out=None, status=0, regex=None):
    """One command for the timeline's shell: (what to type, what must come back). out is the
    exact text it prints (stdout and stderr together), or regex a pattern for it; then the exit
    status must be status."""
    body = regex if regex is not None else "".join(re.escape(l) + r"\r?\n" for l in (out or "").splitlines())
    return (f'{command}; echo "@@ $?"', "(?s)^" + body + rf"@@ {status}\r?\n")


def _lines(*lines):
    return "".join(l + "\n" for l in lines)


def _err(k, name, line, text, col, msg):
    """What ./cc prints for an error at line:col of the file name, whose line is text: from 01.05
    the two lines that point at it, before that the message alone."""
    if k < (1, 5):
        return msg + "\n"
    head = f"{name}:{line}: "
    under = "".join("\t" if c == "\t" else " " for c in text[:col - 1])
    return f"{head}{text}\n{' ' * len(head)}{under}^ {msg}\n"


# try.c, lesson by lesson: its text, its value, and what --tokens, --tree and ./cc make of it.
SUM, PREC, DEEP = "5 + 20 - 4", "1 + 2 * 3 - 4 / 2", "9 - (8 - (7 - (6 - (5 - (4 - (3 - 2))))))"
SUM_TOKENS = _lines("1:1 num 5 5", "1:3 punct +", "1:5 num 20 20", "1:8 punct -", "1:10 num 4 4", "1:11 eof")
PREC_TOKENS = _lines("1:1 num 1 1", "1:3 punct +", "1:5 num 2 2", "1:7 punct *", "1:9 num 3 3", "1:11 punct -",
                     "1:13 num 4 4", "1:15 punct /", "1:17 num 2 2", "1:18 eof")
SUM_TREE = _lines("-", "  +", "    num 5", "    num 20", "  num 4")
PREC_TREE = _lines("-", "  +", "    num 1", "    *", "      num 2", "      num 3", "  /", "    num 4", "    num 2")
DEEP_TREE = _lines("-", "  num 9", "  -", "    num 8", "    -", "      num 7", "      -", "        num 6",
                   "        -", "          num 5", "          -", "            num 4", "            -",
                   "              num 3", "              num 2")
SUM_WALKED = _lines("  .globl main", "main:", "  li a0, 5", "  li t0, 20", "  add a0, a0, t0", "  li t0, 4",
                    "  sub a0, a0, t0", "  ret")
PREC_CODE = _lines("  .globl main", "main:", "  li t0, 1", "  li t1, 2", "  li t2, 3", "  mul t1, t1, t2",
                   "  add t0, t0, t1", "  li t1, 4", "  li t2, 2", "  div t1, t1, t2", "  sub t0, t0, t1",
                   "  mv a0, t0", "  ret")
DEEP_CODE = _lines("  .globl main", "main:", "  li t0, 9", "  li t1, 8", "  li t2, 7", "  li t3, 6", "  li t4, 5",
                   "  li t5, 4", "  addi sp, sp, -16", "  sd t5, 0(sp)", "  li t5, 3", "  addi sp, sp, -16",
                   "  sd t5, 0(sp)", "  li t5, 2", "  ld t6, 0(sp)", "  addi sp, sp, 16", "  sub t5, t6, t5",
                   "  ld t6, 0(sp)", "  addi sp, sp, 16", "  sub t5, t6, t5", "  sub t4, t4, t5",
                   "  sub t3, t3, t4", "  sub t2, t2, t3", "  sub t1, t1, t2", "  sub t0, t0, t1",
                   "  mv a0, t0", "  ret")


def timeline_boot(lesson_id):
    """The steps for the project at a lesson: what its code can do, and an ordinary error for
    the next thing it cannot. In the walker's forms (01.01 to 02.02) an error comes after some
    of the assembly is written already, as in chibicc's first commits, so those runs send
    standard output to /dev/null."""
    from harness.core import lesson_key
    k = lesson_key(lesson_id)
    S = sh_step
    steps = []
    # Form 1, 00.01 to 00.03: main.c alone, and the file is one number.
    if k < (1, 1):
        form1 = _lines("  .globl main", "main:", "  li a0, 42", "  ret")
        steps += [S("./cc try.c", form1),
                  S("./cc -o try.s try.c && cat try.s", form1),
                  S("./cc two.c", "expected the end of the file after the number\n", status=1),
                  S("./cc missing.c", "cannot open missing.c\n", status=1)]
        if k >= (0, 2):
            steps += [S("./ccrun try.c </dev/null", "", status=42),
                      S("./ccrun missing.c </dev/null", "cannot open missing.c\n", status=1)]
        if k >= (0, 3):
            steps.append(S("./same try.c", "same: status 42\n"))
        return steps

    # From 01.01: tokens. The walker compiles the sample until 02.03, the tree from then on.
    if k < (2, 2):
        steps += [S("./cc try.c", SUM_WALKED), S("./cc --tokens try.c", SUM_TOKENS),
                  S("./ccrun try.c </dev/null", "", status=21), S("./same try.c", "same: status 21\n")]
    elif k < (2, 3):
        # 02.02: the parser takes "*", but the walker that still makes the code does not.
        walked = _err(k, "try.c", 1, PREC, 7, "expected '-'")
        steps += [S("./cc --tokens try.c", PREC_TOKENS), S("./cc try.c >/dev/null", walked, status=1),
                  S("./ccrun try.c </dev/null", walked, status=1), S("./same try.c", walked, status=2)]
    elif k < (2, 6):
        steps += [S("./cc --tokens try.c", PREC_TOKENS), S("./cc try.c", PREC_CODE),
                  S("./ccrun try.c </dev/null", "", status=5), S("./same try.c", "same: status 5\n")]
    else:
        steps += [S("./cc try.c", DEEP_CODE), S("./ccrun try.c </dev/null", "", status=4),
                  S("./same try.c", "same: status 4\n")]
    steps.append(S("./ccrun missing.c </dev/null", "cannot open missing.c\n", status=1))

    # 01.01 knows "+" and "-"; 01.02 every punctuator, by longest match.
    if k < (1, 2):
        steps.append(S("./cc --tokens punct.c", _err(k, "punct.c", 1, "1 >>= 2 -> 3", 3, "invalid token"), status=1))
    else:
        steps.append(S("./cc --tokens punct.c", _lines("1:1 num 1 1", "1:3 punct >>=", "1:7 num 2 2",
                                                     "1:9 punct ->", "1:12 num 3 3", "1:13 eof")))
    # 01.03: identifiers and keywords.
    if k < (1, 3):
        steps.append(S("./cc --tokens ident.c", _err(k, "ident.c", 1, "return x1 _y", 1, "invalid token"), status=1))
    else:
        steps.append(S("./cc --tokens ident.c", _lines("1:1 keyword return", "1:8 ident x1", "1:11 ident _y",
                                                     "1:13 eof")))
    # 01.04: comments, strings, character constants, other bases. Before it, "/" is the first
    # thing the scanner cannot read at 01.01, and the '"' after the comment's words from 01.02.
    lit = "/* a comment */ \"a\\tb\" '\\n' 0x1F 017 0b101 // the end"
    if k < (1, 2):
        steps.append(S("./cc --tokens lit.c", _err(k, "lit.c", 1, lit, 1, "invalid token"), status=1))
    elif k < (1, 4):
        steps.append(S("./cc --tokens lit.c", _err(k, "lit.c", 1, lit, 17, "invalid token"), status=1))
    else:
        steps.append(S("./cc --tokens lit.c", _lines('1:17 str "a\\tb" 3', "1:24 num '\\n' 10", "1:29 num 0x1F 31",
                                                   "1:34 num 017 15", "1:38 num 0b101 5", "1:54 eof")))
    # 01.05: an error points at its place; the end of the file is on its last line.
    if k < (2, 1):
        steps.append(S("./cc end.c >/dev/null", _err(k, "end.c", 2, "\t2 +", 5, "expected a number"), status=1))
    else:
        steps.append(S("./cc end.c", _err(k, "end.c", 2, "\t2 +", 5, "expected an expression"), status=1))
    if k < (2, 1):
        return steps

    # From 02.01: the tree. "*" and parentheses from 02.02.
    steps.append(S("./cc --tree try.c", SUM_TREE if k < (2, 2) else PREC_TREE if k < (2, 6) else DEEP_TREE))
    if k < (2, 2):
        steps.append(S("./cc --tree mul.c", _err(k, "mul.c", 1, "1 * 2", 3, "extra token"), status=1))
    elif k < (2, 3):
        steps += [S("./cc --tree mul.c", _lines("*", "  num 1", "  num 2")),
                  S("./cc mul.c >/dev/null", _err(k, "mul.c", 1, "1 * 2", 3, "expected '-'"), status=1)]
    if k < (2, 3):
        return steps

    # From 02.03: code from the tree, for each level as it comes.
    steps += [S("./ccrun mul.c </dev/null", "", status=2), S("./same mul.c", "same: status 2\n")]
    if k < (2, 4):
        steps.append(S("./cc ops.c", _err(k, "ops.c", 1, "6 % 4 << 2 | 1", 3, "extra token"), status=1))
    else:
        steps += [S("./ccrun ops.c </dev/null", "", status=9), S("./same ops.c", "same: status 9\n")]
    if k < (2, 5):
        steps.append(S("./cc cmp.c", _err(k, "cmp.c", 1, "-3 < 2 == !0", 1, "expected an expression"), status=1))
    else:
        steps += [S("./ccrun cmp.c </dev/null", "", status=1), S("./same cmp.c", "same: status 1\n")]
    deep = "1 - (2 - (3 - (4 - (5 - (6 - 7)))))"
    if k < (2, 6):
        steps.append(S("./cc deep.c >/dev/null",
                       _err(k, "deep.c", 1, deep, 28, "out of registers: the expression is too deep"), status=1))
    else:
        steps += [S("./ccrun deep.c </dev/null", "", status=4), S("./same deep.c", "same: status 4\n")]
    return steps
