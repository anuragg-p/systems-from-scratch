"""Track lang: your own language, chapter by chapter, read beside Programming Language Pragmatics.

Module NN is chapter NN of the book (4th edition). Chapter 1's project, built by make with the
host's C compiler: machine (a RISC-V machine that runs assembly text), gcd (the C program,
with rt.o), mote0 (the first interpreter, and a prompt), mote2c and motec (the translator to C,
and the script that compiles and links what it writes), agree (every program, every way), and
mote: the compiler's phases (scan.c, parse.c, analyze.c), then interp.c, or gen.c and
improve.c for the machine. No RISC-V toolchain is needed; when riscv64-elf-as (or another
RISC-V as) is installed, the tests also hold every .s to it.

Fixtures the lesson tests use (t is the test's context):

    exe(t, name)            the path of one of the project's programs (machine, gcd, mote0,
                            mote2c, mote): ./name, or with LANG_SANITIZE=1 the same sources built
                            with AddressSanitizer and UBSan outside the track, once per run
    write(t, name, text)    a file in the test's scratch directory: its path
    prog(t, name, argv, input="", cwd=None)
                            a program run with stdin from input: (status, stdout, stderr); fails on
                            a sanitizer report or after 60 s
    machine(t, asm, input="", *flags)     the machine on asm (a file t1.s ...): (status, out, err)
    mote0(t, src, input="", *flags)       mote0 on src (a file t1.mote ...)
    mote2c(t, src)                        mote2c on src: (status, C, err)
    motec(t, src, input="")               ./motec on src in the scratch directory, then the program
                                          it made: (status, out, err); status is motec's if it failed
    mote(t, src, *flags, input="")        mote with flags on src
    compiled(t, src, input="", opt=False) mote -S [-O] on src, then the machine on what it wrote:
                                          (status, out, err); fails if mote -S fails
    asm(t, src, opt=False)                the assembly of mote -S [-O] on src; fails if mote fails
    ways(t, src, input, have)             src run each way in have ("mote0", "motec", "mote",
                                          "machine", "machine -O"): {way: (status, out, err)}
    error_at(err)                         "FILE:LINE:COL: message" (or FILE:LINE:) parsed:
                                          (line, col or None, message)
    gen()                                 tests/proggen.py: the reference and the random programs
    assembles(t, text)                    a RISC-V as (when one is installed) assembles text with
                                          -march=rv64im, or the test fails; False when there is none
    warnings(t)                           every program's sources compiled with -std=c11 -Wall
                                          -Wextra -pedantic -Werror: what the compiler said, ""
    script(t, name, *args, cwd=None)      one of the project's scripts (motec, agree)

Tests are internal. With a lesson's code cut out, its test fails at the stub: "lang: NN.LL: <what>
not written yet", exit status 3.
"""

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading

try:
    from harness.core import Fail
except ImportError:          # run as a program (tests/fuzz.py loads this file too)
    class Fail(Exception):
        pass

TITLE = "Your own language, chapter by chapter"
KIND = "language"
SUMMARY = ("A language of your own, built in C a chapter of Programming Language Pragmatics at a "
           "time: a machine, two interpreters, a translator to C and a compiler, all held to one answer.")

# What this track is built on (harness/web/views.py, upstreams()). No code is taken from either.
UPSTREAM = [
    {"name": "The RISC-V Instruction Set Manual",
     "url": "https://github.com/riscv/riscv-isa-manual",
     "licence": "CC-BY-4.0",
     "owes": "No code. The machine runs RISC-V assembly text: its registers, instructions and their "
             "meaning, division by zero included, are as the manual defines them.",
     "derived": False},
    {"name": "chibicc",
     "url": "https://github.com/rui314/chibicc",
     "licence": "MIT",
     "owes": "No code. The scanner and the parser take its shape: a list of tokens, and a function "
             "for each rule of the grammar.",
     "derived": False},
]

# Files that may hold "@build NN.LL" regions (harness/workspace.py), and what a cut region becomes:
# todo() (@internal in each program) prints "lang: NN.LL: <what> not written yet" and exits 3; in
# the scripts, the same from the shell.
SOURCES = ["*.c", "*.h", "motec", "agree"]
STUBS = {
    ".c": 'todo("{id}", "{title}");',
    "": 'echo "lang: {id}: {title} not written yet" >&2; exit 3',
}
# Not for learners: the notes for the lesson writers, and what make builds.
HIDDEN = ["NOTES.md", "machine", "gcd", "mote0", "mote2c", "mote", "*.o", "*.dSYM/*"]
# When each file comes into the project (harness/timeline.py): a file with regions comes with its
# first region's lesson; the others are named here.
FILES_FROM = {
    "Makefile": "01.01",
    "programs/gcd.s": "01.01",
    "programs/gcd.in": "01.01",
    "programs/gcd.c": "01.02",
    "programs/*.mote": "01.02",
    "programs/*.out": "01.02",
    "programs/sum.in": "01.02",
    "programs/primes.in": "01.02",
    "rt.h": "01.02",
    "mote.h": "01.06",
}

PROGRAMS = {          # each program of the project, and the sources it is built from
    "machine": ["machine.c"],
    "gcd": ["programs/gcd.c", "rt.c"],
    "mote0": ["mote0.c"],
    "mote2c": ["mote2c.c"],
    "mote": ["main.c", "scan.c", "parse.c", "analyze.c", "interp.c", "gen.c", "improve.c"],
}


def build(t):
    t.run(["make", "-s"])


# ---------------------------------------------------------------- run it
#
# The track contract's optional hooks: prepare(root) builds the project, run_argv(root) runs it;
# both from the project's directory (./learn run lang --at NN.LL, or the finished track).

def prepare(root):
    return ["make", "-s"]


SAMPLES = [   # (the file that comes with the lesson, the lesson's sample command)
    ("improve.c", "./mote -S -O programs/gcd.mote > build/gcd.s && ./machine --count build/gcd.s < programs/gcd.in"),
    ("gen.c", "./mote -S programs/gcd.mote > build/gcd.s && ./machine --count build/gcd.s < programs/gcd.in"),
    ("interp.c", "./mote programs/gcd.mote < programs/gcd.in"),
    ("analyze.c", "./mote --tree programs/gcd.mote"),
    ("parse.c", "./mote --parse-tree programs/gcd.mote"),
    ("scan.c", "./mote --tokens programs/gcd.mote"),
    ("agree", "./agree"),
    ("motec", "./motec programs/gcd.mote && build/gcd < programs/gcd.in"),
    ("mote0.c", "./mote0 programs/gcd.mote < programs/gcd.in"),
    ("rt.c", "./gcd < programs/gcd.in"),
    ("machine.c", "./machine programs/gcd.s < programs/gcd.in"),
]
NAMED = ("machine", "gcd", "mote0", "mote2c", "motec", "agree", "mote")


def run_argv(root, args=()):
    """With no args, the sample of the lesson the project stands at (the newest of its files
    names it), through sh -c from the project's directory: at 01.10, ./mote -S programs/gcd.mote >
    build/gcd.s && ./machine --count build/gcd.s < programs/gcd.in. With args: one of the
    project's programs when the first names it (./learn run lang -- mote0 programs/sum.mote),
    else ./mote (./mote0 before mote exists) with them all."""
    args = list(args)
    if args:
        name = args[0][2:] if args[0].startswith("./") else args[0]
        if name in NAMED and os.path.exists(os.path.join(root, name)):
            return ["./" + name] + args[1:]
        return (["./mote"] if os.path.exists(os.path.join(root, "main.c")) else ["./mote0"]) + args
    command = next(c for f, c in SAMPLES if os.path.exists(os.path.join(root, f)))
    return ["/bin/sh", "-c", command]


# ---------------------------------------------------------------- the programs under test

_san_lock = threading.Lock()
_san = {}
SANITIZER = re.compile(r"AddressSanitizer|UndefinedBehaviorSanitizer|runtime error:|LeakSanitizer")


def exe(t, name):
    """./name of the tree under test, or with LANG_SANITIZE=1 the same sources built with ASan and
    UBSan in a directory of their own (once per tree per run)."""
    if not os.environ.get("LANG_SANITIZE"):
        return os.path.join(t.root, name)
    os.environ.setdefault("ASAN_OPTIONS", "detect_leaks=0")   # memory is never freed, on purpose
    with _san_lock:
        key = (t.root, name)
        if key not in _san:
            out = tempfile.mkdtemp(prefix="lang-sanitize-")
            srcs = [s for s in PROGRAMS[name] if os.path.exists(os.path.join(t.root, s))]
            r = subprocess.run([os.environ.get("HOSTCC", "cc"), "-std=c11", "-g", "-O1", "-I.",
                                "-fno-omit-frame-pointer", "-fsanitize=address,undefined",
                                "-fno-sanitize-recover=all", "-o", os.path.join(out, name)] + srcs,
                               cwd=t.root, capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                raise Fail(f"the sanitizer build of {name} failed:\n{r.stderr[-2000:]}")
            _san[key] = os.path.join(out, name)
        return _san[key]


def write(t, name, text):
    path = os.path.join(t.tmp, name)
    with open(path, "wb") as f:
        f.write(text.encode("latin-1") if isinstance(text, str) else text)
    return path


def _file(t, src, ext):
    t._lang_files = getattr(t, "_lang_files", 0) + 1
    name = f"t{t._lang_files}{ext}"
    write(t, name, src)
    return name


def prog(t, name, argv, input="", cwd=None, timeout=60):
    """The program `name` with argv, from cwd (the scratch directory), stdin from input."""
    try:
        r = subprocess.run([exe(t, name)] + list(argv), cwd=cwd or t.tmp, capture_output=True,
                           input=input.encode("latin-1") if isinstance(input, str) else input,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        raise Fail(f"{name} {' '.join(argv)} did not stop within {timeout} s")
    out, err = r.stdout.decode("latin-1"), r.stderr.decode("latin-1")
    if SANITIZER.search(err):
        raise Fail(f"{name} {' '.join(argv)}: a sanitizer report:\n{err[-3000:]}")
    return r.returncode, out, err


def machine(t, asm, input="", *flags):
    return prog(t, "machine", list(flags) + [_file(t, asm, ".s")], input)


def mote0(t, src, input="", *flags):
    return prog(t, "mote0", list(flags) + [_file(t, src, ".mote")], input)


def mote2c(t, src):
    return prog(t, "mote2c", [_file(t, src, ".mote")])


def mote(t, src, *flags, input=""):
    return prog(t, "mote", list(flags) + [_file(t, src, ".mote")], input)


def script(t, name, *args, cwd=None, input=""):
    try:
        r = subprocess.run([os.path.join(t.root, name)] + list(args), cwd=cwd or t.tmp,
                           capture_output=True, input=input.encode(), timeout=300)
    except subprocess.TimeoutExpired:
        raise Fail(f"{name} {' '.join(args)} did not finish within 300 s")
    return r.returncode, r.stdout.decode("latin-1"), r.stderr.decode("latin-1")


def motec(t, src, input=""):
    name = _file(t, src, ".mote")
    st, out, err = script(t, "motec", name)
    if st != 0:
        return st, out, err
    try:
        r = subprocess.run([os.path.join(t.tmp, "build", name[:-5])], cwd=t.tmp, capture_output=True,
                           input=input.encode(), timeout=60)
    except subprocess.TimeoutExpired:
        raise Fail(f"the program motec made of {name} did not stop within 60 s")
    return r.returncode, r.stdout.decode("latin-1"), r.stderr.decode("latin-1")


def asm(t, src, opt=False):
    st, out, err = mote(t, src, "-S", *(["-O"] if opt else []))
    if st != 0:
        raise Fail(f"mote -S{' -O' if opt else ''} failed (status {st}) on:\n{src}\n{err}")
    return out


def compiled(t, src, input="", opt=False):
    return machine(t, asm(t, src, opt), input)


WAYS = ("mote0", "motec", "mote", "machine", "machine -O")


def ways(t, src, input, have=WAYS):
    out = {}
    for w in have:
        if w == "mote0":
            out[w] = mote0(t, src, input)
        elif w == "motec":
            out[w] = motec(t, src, input)
        elif w == "mote":
            out[w] = mote(t, src, input=input)
        else:
            out[w] = compiled(t, src, input, opt=w.endswith("-O"))
    return out


ERROR = re.compile(r"^(?:\S+?):(\d+):(?:(\d+):)? (.*)$")


def error_at(err):
    """The first line of stderr as (line, col or None, message), or a Fail."""
    m = ERROR.match(err.split("\n")[0])
    if not m:
        raise Fail(f"not an error of the form FILE:LINE[:COL]: message: {err!r}")
    return int(m.group(1)), int(m.group(2)) if m.group(2) else None, m.group(3)


_gen = None


def gen():
    global _gen
    if _gen is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "proggen.py")
        spec = importlib.util.spec_from_file_location("lang_proggen", path)
        _gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_gen)
    return _gen


AS_PREFIXES = ("riscv64-elf-", "riscv64-unknown-elf-", "riscv64-linux-gnu-")


def assembles(t, text):
    """text assembled by a RISC-V as, if there is one: True, or a Fail with what it said. False
    when none is installed (the machine is this track's own; the real assembler is a check)."""
    tool = next((p + "as" for p in AS_PREFIXES if shutil.which(p + "as")), None)
    if not tool:
        return False
    path = _file(t, text, ".s")
    r = subprocess.run([tool, "-march=rv64im", "-mabi=lp64", "-o", os.devnull, path], cwd=t.tmp,
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise Fail(f"{tool} does not take {path}:\n{r.stderr}\n{text}")
    return True


def warnings(t):
    said = []
    for name, srcs in PROGRAMS.items():
        srcs = [s for s in srcs if os.path.exists(os.path.join(t.root, s))]
        r = subprocess.run([os.environ.get("HOSTCC", "cc"), "-std=c11", "-Wall", "-Wextra", "-pedantic",
                            "-Werror", "-fsyntax-only", "-I."] + srcs, cwd=t.root, capture_output=True,
                           text=True, timeout=120)
        said.append((r.stdout + r.stderr).strip())
    return "\n".join(s for s in said if s)


def parallel(t, fn, items, jobs=None):
    """fn(item) for every item on a few threads; fails naming the items that failed (ten shown)."""
    from concurrent.futures import ThreadPoolExecutor

    def one(item):
        try:
            fn(item)
            return None
        except Fail as e:
            return f"{item!r}: {e}"
    with ThreadPoolExecutor(jobs or min(8, os.cpu_count() or 1)) as pool:
        bad = [r for r in pool.map(one, items) if r]
    if bad:
        raise Fail(f"{len(bad)} of {len(items)} failed:\n" + "\n".join(bad[:10]))


class Scratch:
    """What the fixtures need of a test's t, for another thread: the same tree, its own scratch
    directory (inside t's)."""

    def __init__(self, t, name):
        self.root, self.tmp = t.root, os.path.join(t.tmp, name)
        os.makedirs(self.tmp, exist_ok=True)


# ---------------------------------------------------------------- the project at each lesson
#
# Internal: ./learn check-timeline lang builds the project as the site shows it at each lesson
# (harness/timeline.py), writes the sample files below into it (timeline_run) and starts a shell
# there. timeline_boot types commands into it, each followed by echo "@@ $?", and checks exactly
# what each prints and its status: each lesson's sample, and for what a later lesson brings, an
# ordinary error, never a crash or a stub.

TIMELINE_FAIL = [r"not written yet", r"Segmentation fault", r"Abort", r"core dumped", r"Bus error",
                 r"AddressSanitizer", r"runtime error:"]

TIMELINE_FILES = {
    "mem.s": "main:\n    li   t0, 7\n    sd   t0, -8(sp)\n    ld   a0, -8(sp)\n    ret\n",
    "neg.s": "main:\n    li   a0, 5\n    neg  a0, a0\n    call putint\n    li   t1, 0\n    div  a0, a0, t1\n"
             "    call putint\n    call exit\n",
    "block.in": "x := 6\nwhile x > 4 do\nwrite x\nx := x - 1\nend\nwrite y\nwrite x * 7\n",
    "flow.mote": "read n while n > 0 do write n n := n - 1 end\n",
    "late.mote": "write 1\nx := y + 1\n",
    "zero.mote": "read a\nb := 0\nwrite a / b\n",
    "deep.mote": "x := 1 - (2 - (3 - (4 - (5 - (6 - (7 - 8))))))\nwrite x\n",
    "oops.mote": "x := 1 +\nwrite x\n",
}
GCD_TOKENS = ["2:1 keyword read", "2:6 name i", "3:1 keyword read", "3:6 name j", "4:1 keyword while",
              "4:7 name i", "4:9 op !=", "4:12 name j", "4:14 keyword do", "5:5 keyword if", "5:8 name i",
              "5:10 op >", "5:12 name j", "5:14 keyword then", "6:9 name i", "6:11 op :=", "6:14 name i",
              "6:16 op -", "6:18 name j", "7:5 keyword else", "8:9 name j", "8:11 op :=", "8:14 name j",
              "8:16 op -", "8:18 name i", "9:5 keyword end", "10:1 keyword end", "11:1 keyword write",
              "11:7 name i", "11:8 eof"]
FLOW_PARSE = ["program", "  stmt", "    keyword read", "    name n", "  stmt", "    keyword while", "    cond",
              "      expr", "        term", "          factor", "            name n", "      op >",
              "      expr", "        term", "          factor", "            number 0", "    keyword do",
              "    stmt", "      keyword write", "      expr", "        term", "          factor",
              "            name n", "    stmt", "      name n", "      op :=", "      expr", "        term",
              "          factor", "            name n", "        op -", "        term", "          factor",
              "            number 1", "    keyword end"]
GCD_TREE = ["read i#1", "read j#2", "while (!= i#1 j#2)", "  if (> i#1 j#2)", "    := i#1 (- i#1 j#2)",
            "  else", "    := j#2 (- j#2 i#1)", "write i#1"]


def timeline_run(root):
    for name, text in TIMELINE_FILES.items():
        with open(os.path.join(root, name), "w") as f:
            f.write(text)
    return ["/bin/sh"]


def sh_step(command, out=None, status=0, regex=None):
    """One command for the timeline's shell: what it prints (stdout and stderr together; exactly
    out, or regex), then its exit status."""
    body = regex if regex is not None else "".join(re.escape(l) + r"\r?\n" for l in (out or "").splitlines())
    return (f'{command}; echo "@@ $?"', "(?s)^" + body + rf"@@ {status}\r?\n")


def _lines(*lines):
    return "".join(l + "\n" for l in lines)


def usage(k):
    """mote's usage line at lesson k: the options there are; before 01.09 one is needed."""
    opts = "--tokens" + (" | --parse-tree" if k >= (1, 7) else "") + \
        (" | --tree | --symbols" if k >= (1, 8) else "") + (" | -S" if k >= (1, 10) else "") + \
        (" [-O]" if k >= (1, 11) else "")
    return f"usage: mote [{opts}] FILE\n" if k >= (1, 9) else f"usage: mote ({opts}) FILE\n"


def agree_out(k):
    names = ["mote0", "motec"] + (["mote"] if k >= (1, 9) else []) + (["machine"] if k >= (1, 10) else []) + \
        (["machine -O"] if k >= (1, 11) else [])
    row = "  ".join(f"{n} ok" for n in names)
    return _lines(f"gcd     {row}", f"primes  {row}", f"sum     {row}",
                  f"3 programs, {len(names)} ways each: all agree")


def timeline_boot(lesson_id):
    from harness.core import lesson_key
    k = lesson_key(lesson_id)
    S = sh_step
    steps = [S("./machine programs/gcd.s < programs/gcd.in", "21\n"),
             S("./machine --count programs/gcd.s < programs/gcd.in", "21\n53 instructions\n"),
             S("./machine neg.s", "-5\n-1\n", status=255)]
    if k < (1, 10):
        steps.append(S("./machine mem.s", "machine: mem.s:3: unknown instruction 'sd'\n", status=1))
    else:
        steps.append(S("./machine mem.s", "", status=7))
    if k >= (1, 2):
        steps += [S("./gcd < programs/gcd.in", "21\n"), S("./gcd < /dev/null", "getint: no more input\n", status=1)]
    if k >= (1, 3):
        steps += [S("./mote0 --count programs/gcd.mote < programs/gcd.in", "21\n88 lines read\n"),
                  S("./mote0 late.mote", "1\nlate.mote:2: y has no value yet\n", status=1)]
    if k == (1, 3) or k == (1, 4):
        steps.append(S("./mote0 < block.in", "usage: mote0 [--count] FILE\n", status=2))
    if k >= (1, 4):
        steps += [S("./motec programs/gcd.mote && build/gcd < programs/gcd.in", "21\n"),
                  S("./mote2c programs/gcd.mote | head -4", _lines('#include "rt.h"', "", "int main(void) {",
                                                                 "    long i = 0;"))]
    if k >= (1, 5):
        steps += [S("./mote0 < block.in", "> > . . . 6\n5\n> line 6: y has no value yet\n> 28\n> \n"),
                  S("./agree", agree_out(k))]
    if k < (1, 6):
        return steps
    steps += [S("./mote --tokens programs/gcd.mote", _lines(*GCD_TOKENS)),
              S("./mote --tokens oops.mote | tail -2", _lines("2:7 name x", "2:8 eof"))]
    if k < (1, 9):
        steps.append(S("./mote programs/gcd.mote", usage(k), status=2))
    if k >= (1, 7):
        steps += [S("./mote --parse-tree flow.mote", _lines(*FLOW_PARSE)),
                  S("./mote --parse-tree oops.mote", "oops.mote:2:1: expected a number, a name or '('\n", status=1),
                  S("./mote --parse-tree programs/gcd.mote | wc -l | tr -d ' '", "64\n")]
    if k >= (1, 8):
        steps += [S("./mote --tree programs/gcd.mote", _lines(*GCD_TREE)),
                  S("./mote --symbols programs/gcd.mote", _lines("1 i 2:6", "2 j 3:6")),
                  S("./mote --tree late.mote", "late.mote:2:6: y is used before anything gives it a value\n", status=1)]
    if k >= (1, 9):
        steps += [S("./mote programs/gcd.mote < programs/gcd.in", "21\n"),
                  S("echo 5 | ./mote flow.mote", _lines("5", "4", "3", "2", "1")),
                  S("echo 5 | ./mote zero.mote", "zero.mote:3:9: division by zero\n", status=1),
                  S("./mote programs/gcd.mote < /dev/null", "programs/gcd.mote:2:1: read: no more input\n", status=1)]
    if k >= (1, 10):
        steps += [S("./mote -S programs/gcd.mote > build/gcd.s && ./machine --count build/gcd.s < programs/gcd.in",
                    "21\n142 instructions\n"),
                  S("./mote -S zero.mote > build/zero.s && echo 5 | ./machine build/zero.s",
                    "line 3: division by zero\n", status=1),
                  S("./mote -S deep.mote > /dev/null", "deep.mote:1:40: expression too deep\n", status=1)]
    if k >= (1, 10) and k < (1, 11):
        steps.append(S("./mote -S -O programs/gcd.mote", usage(k), status=2))
    if k >= (1, 11):
        steps.append(S("./mote -S -O programs/gcd.mote > build/gcd.s && ./machine --count build/gcd.s"
                       " < programs/gcd.in", "21\n61 instructions\n"))
    return steps
