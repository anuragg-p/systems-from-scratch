"""make: reads a makefile and builds what is out of date, in order (module 07). T is track.py.

Our make is bin/make; the system's is `make` from PATH (GNU make 3.81 on macOS, GNU make 4 on
Linux). Both run with LC_ALL=C and without MAKEFLAGS, in a directory of the test's own.

    ours(t, cwd, args, env=None, check=True)
                        bin/make args in cwd: a Result
    theirs(t, cwd, args, check=True)
                        the system's make args in cwd: a Result
    case(t, name, text, files=None)
                        a fresh directory holding text as its Makefile (and files, {path: text}):
                        its path
    project(t)          a copy of the project's Makefile, lib/ and tools/ in a fresh directory:
                        its path
    message(text)       a make message with the system's quotes (`x' in 3.81) and name made ours
    graph(text)         --graph's output: (names in order, {name: [needs]}, {phony names})
    database(text)      the system make's -p database: {target: [prerequisites]}, for the targets
                        that have some (GNU's own built-in suffix rules left out)
    reachable(needs, goals)
                        the names the goals need, and the goals: a set
    valid_order(order, needs)
                        the first (name, need) pair that order puts the wrong way round, or None
    tsort_agrees(t, order, needs)
                        the system's tsort, given every edge and order's own sequence, prints
                        exactly order (it would print a cycle if order broke an edge)
    trace(err)          the DS_TRACE=1 lines: [(event, [words])]
    stamp(cwd, names, when)
                        set the modification time of each file to when (seconds)
    CASES               the differential table: {name: (makefile text, extra files, goals, leaf)}
    differential(t, name, args=())
                        one CASES entry, built by ours and the system's side by side: -n output
                        on a clean directory, a real run (its log and files), a second run, and
                        -n after the leaf is newer; each must be the same
"""

import os
import re
import shutil

from harness.core import Fail

PROGRAMS = {"make": "07.01"}
FILES_FROM = {
    "tools/make/tool.mk": "07.01",
    "tools/make/make.h": "07.01",
    "lib/depgraph.h": "07.01",
    "lib/readyq.h": "07.04",
    "tools/make/examples/diamond.mk": "07.01",
    "tools/make/examples/cycle.mk": "07.01",
    "tools/make/examples/slow.mk": "07.04",
    "tools/make/gen.py": "07.03",
}
HIDDEN = ["tools/make/NOTES.md"]
UPSTREAM = [
    {"name": "GNU make",
     "url": "https://www.gnu.org/software/make/",
     "licence": "GPL-3.0-or-later",
     "owes": "No code. Our make reads the part of the makefile language this track's Makefile uses "
             "and runs the same commands, in the same order, as GNU make 3.81 and 4.",
     "derived": False},
]


def _env(extra=None):
    env = T._env(extra)
    for k in ("MAKEFLAGS", "MFLAGS", "MAKELEVEL", "MAKEFILES", "GNUMAKEFLAGS"):
        env.pop(k, None)
    env["ZERO_AR_DATE"] = "1"         # macOS's ld and ar: no file times in what they write
    return env


def ours(t, cwd, args, env=None, check=True, timeout=300):
    root = T._root(t)
    return T._exec([os.path.join(root, "bin", "make")] + [str(a) for a in args], None, _env(env), check, cwd,
                   timeout)


def theirs(t, cwd, args, check=True, timeout=300):
    exe = shutil.which("make")
    if exe is None:
        raise Fail("no make on this machine")
    return T._exec([exe] + [str(a) for a in args], None, _env(), check, cwd, timeout)


def case(t, name, text, files=None):
    d = os.path.join(t.tmp, name)
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)
    for path, body in dict(files or {}, Makefile=text).items():
        p = os.path.join(d, path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(body)
    return d


def project(t, name="project"):
    root = T._root(t)
    d = os.path.join(t.tmp, name)
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)
    shutil.copy(os.path.join(root, "Makefile"), d)
    for sub in ("lib", "tools"):
        shutil.copytree(os.path.join(root, sub), os.path.join(d, sub),
                        ignore=shutil.ignore_patterns("__pycache__", "*.o"))
    return d


def message(text):
    """GNU make 3.81 quotes `like this'; 4 'like this'. And the program may be called gmake."""
    text = re.sub(r"`([^'`]*)'", r"'\1'", text)
    return re.sub(r"^g?make(\[\d+\])?: ", "make: ", text, flags=re.M)


def graph(text):
    names, needs, phony = [], {}, set()
    for line in text.splitlines():
        head, _, rest = line.partition(":")
        if head == ".PHONY":
            phony |= set(rest.split())
            continue
        names.append(head)
        needs[head] = rest.split()
    return names, needs, phony


def database(text):
    out = {}
    files = text.split("\n# Files\n", 1)[-1]
    for line in files.splitlines():
        m = re.match(r"^([^#\s.][^:=]*): (.+)$", line)
        if m and not line.startswith("\t"):
            out[m.group(1).strip()] = m.group(2).split()
    return out


def reachable(needs, goals):
    seen, todo = set(), list(goals)
    while todo:
        n = todo.pop()
        if n in seen:
            continue
        seen.add(n)
        todo += needs.get(n, [])
    return seen


def valid_order(order, needs):
    at = {n: i for i, n in enumerate(order)}
    for n in order:
        for m in needs.get(n, []):
            if at.get(m, len(order)) > at[n]:
                return (n, m)
    return None


def tsort_agrees(t, order, needs):
    if not T.have("tsort"):
        return None
    pairs = [f"{m} {n}" for n in order for m in needs.get(n, [])]
    pairs += [f"{a} {b}" for a, b in zip(order, order[1:])] or [f"{order[0]} {order[0]}"]
    r = T._exec([shutil.which("tsort")], "\n".join(pairs) + "\n", T._env(), False, t.tmp, 60)
    if r.out.split() != order or r.err:
        raise Fail(f"tsort does not agree with our order:\n  ours:  {order}\n  tsort: {r.out.split()}\n{r.err}")
    return True


def trace(err):
    out = []
    for line in err.splitlines():
        if line.startswith("trace: "):
            words = line[7:].split()
            out.append((words[0], words[1:]))
    return out


def stamp(cwd, names, when):
    for n in names:
        p = os.path.join(cwd, n)
        if os.path.exists(p):
            os.utime(p, (when, when))


def _files(d):
    out = {}
    for dirpath, _, filenames in os.walk(d):
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, d)
            with open(p, "rb") as f:
                out[rel] = f.read()
    return out


# The differential table: makefiles on which GNU make 3.81 and 4 agree, and ours must agree with
# both. Each: (Makefile, other files, goals on the command line, a file to make newer afterwards).
# Every recipe logs its target's name to "log", so a real run can be compared too.
CASES = {
    "chain": ("""\
a: b
\techo a >> log; touch a
b: c
\techo b >> log; touch b
c:
\techo c >> log; touch c
""", {}, [], "c"),
    "diamond": ("""\
app: liba libb
\techo app >> log; touch app
liba: common.h
\techo liba >> log; touch liba
libb: common.h
\techo libb >> log; touch libb
common.h: src.h
\techo common.h >> log; cp src.h common.h
""", {"src.h": "int x;\n"}, [], "src.h"),
    "variables": ("""\
CC = echo cc
OBJS = one.o
OBJS += two.o   # a comment after blanks: they stay in the value
FLAGS = -O$(LEVEL) $(EXTRA)
LEVEL = 2
WHICH = OBJS
D = $$
prog: $($(WHICH))
\t$(CC) $(FLAGS) -o prog $(OBJS) >> log
\techo '[$(OBJS)]' >> log; echo $(D)HOME is not expanded by make >> log; touch prog
one.o two.o: defs.h
\techo $(CC) $(FLAGS) one >> log; touch one.o two.o
FLAGS += -g
""", {"defs.h": ""}, [], "defs.h"),
    "rules": ("""\
all: t1 t2 t2 t1
t1: c d
t1: e
\techo t1 >> log; touch t1
t1: f c
t2:
\techo t2 >> log
c:
\techo c >> log
d:
\techo d >> log
e f:
\techo '$$$$-free' >> log; echo one of e and f >> log
f: c
.PHONY: all t2
""", {}, [], None),
    "phony": ("""\
out: gen in.txt
\techo out >> log; cat in.txt > out
gen:
\techo gen >> log
clean:
\trm -f out log
.PHONY: gen clean
""", {"in.txt": "x\\n"}, [], "in.txt"),
    "include": ("""\
TOOLS = base
all:
include parts/*.mk
all: $(TOOLS)
\techo all: $(TOOLS) >> log
base:
\techo base >> log; touch base
.PHONY: all
""", {"parts/b.mk": "TOOLS += b\nb: base\n\techo b >> log; touch b\n",
      "parts/a.mk": "TOOLS += a\na: base\n\techo a >> log; touch a\n"}, [], None),
    "continued": ("""\
NAMES = one \\
        two
all: $(NAMES) \\
     three
\t@echo all >> log
one two three:
\t@echo $(NAMES) >> log
\t  @  echo quiet, after blanks >> log
.PHONY: all
""", {}, [], None),
    "goals": ("""\
first: second
\techo first >> log; touch first
second:
\techo second >> log; touch second
third: second
\techo third >> log; touch third
""", {}, ["third", "first"], "second"),
    "cmdvar": ("""\
X = from the makefile
X += and more
show:
\techo '$(X)' >> log
.PHONY: show
""", {}, ["X=from the command line"], None),
    "empty": ("all:\n.PHONY: all\n", {}, [], None),
    "uptodate": ("""\
out: in
\techo out >> log; cp in out
""", {"in": "1\\n"}, [], "in"),
}


def differential(t, name, args=()):
    """Build CASES[name] with ours and the system's make in two directories, side by side."""
    text, files, goals, leaf = CASES[name]
    a = case(t, name + "-ours", text, files)
    b = case(t, name + "-theirs", text, files)
    argv = list(args) + list(goals)
    steps = []

    def both(what, extra=()):
        x = ours(t, a, list(extra) + argv, check=False)
        y = theirs(t, b, list(extra) + argv, check=False)
        T.same(t, message(x.out), message(y.out), f"{name}: {what}: make {' '.join(list(extra) + argv)}")
        if x.rc != y.rc:
            raise Fail(f"{name}: {what}: ours exits {x.rc}, the system's {y.rc}:\n{x}\n{y}")
        steps.append(what)
        return x

    both("-n on a clean directory", ["-n"])
    both("a real run")
    fa, fb = _files(a), _files(b)
    fa.pop("Makefile", None), fb.pop("Makefile", None)
    if fa != fb:
        raise Fail(f"{name}: the runs left different files:\n  ours:   {sorted(fa)}\n  system: {sorted(fb)}\n"
                   f"  ours' log:   {fa.get('log')!r}\n  system's log: {fb.get('log')!r}")
    # every file made at one time, a second apart from GNU 3.81's whole seconds
    when = int(os.path.getmtime(os.path.join(a, "Makefile"))) - 100
    for d in (a, b):
        stamp(d, list(_files(d)), when)
    both("a second run", ["-n"])
    if leaf:
        for d in (a, b):
            stamp(d, [leaf], when + 10)
        both(f"-n with {leaf} newer", ["-n"])
    return steps


# ---------------------------------------------------------------- check-timeline

def timeline_steps(k):
    if k < (7, 1):
        return []
    ex = "tools/make/examples"
    steps = [T.sh_step(f"bin/make --graph -f {ex}/diamond.mk",
                       "app: liba libb\nliba: common.h\nlibb: common.h\ncommon.h:\n")]
    if k < (7, 3):
        steps.append(T.sh_step(f"bin/make -n -f {ex}/diamond.mk",
                               "touch common.h\ntouch liba\ntouch common.h\ntouch libb\ntouch app\n"))
        steps.append(T.sh_step("bin/make --order < /dev/null", "make: unknown option '--order'\n", 2))
    else:
        steps += [T.sh_step(f"bin/make -n -f {ex}/diamond.mk", "touch common.h\ntouch liba\ntouch libb\ntouch app\n"),
                  T.sh_step(f"bin/make --order -f {ex}/diamond.mk", "common.h\nliba\nlibb\napp\n"),
                  T.sh_step(f"bin/make -n --algo=recurse -f {ex}/diamond.mk",
                            "touch common.h\ntouch liba\ntouch common.h\ntouch libb\ntouch app\n")]
    if k < (7, 2):
        steps.append(T.sh_step(f"bin/make -n -f {ex}/cycle.mk",
                               "make: a cycle in what 'all' needs: the walk went deeper than the 4 targets "
                               "there are\n", 2))
    else:
        steps.append(T.sh_step(f"bin/make -n -f {ex}/cycle.mk", "make: dependency cycle: a -> b -> c -> a\n", 2))
    if k < (7, 4):
        steps.append(T.sh_step(f"bin/make -j 2 -f {ex}/diamond.mk", "make: unknown option -j\n", 2))
        if k >= (7, 3):
            steps.append(T.sh_step("bin/make --algo=queue < /dev/null",
                                   "make: no --algo 'queue' (have: recurse, topo)\n", 2))
    else:
        steps.append(T.sh_step(f"bin/make -n -j 2 -f {ex}/diamond.mk",
                               "touch common.h\ntouch liba\ntouch libb\ntouch app\n"))
    return steps


def timeline_after(root, k):
    if k < (7, 1):
        return None
    if not T.have("make"):
        return "make: no system make to compare with"
    env = _env()
    sysmake = shutil.which("make")
    if k < (7, 3):
        # the walk makes everything, by every path: each of the system's commands, at least once
        mine = T._exec([os.path.join(root, "bin", "make"), "-n"], None, env, True, root, 300).out.splitlines()
        want = T._exec([sysmake, "-n", "-B"], None, env, True, root, 300).out.splitlines()
        missing = set(want) - set(mine)
        if missing or len(mine) <= len(want):
            raise Fail(f"bin/make -n at {k}: {len(mine)} commands, the system's make -n -B {len(want)}; "
                       f"missing: {sorted(missing)[:3]}")
        return f"make: the walk's {len(mine)} commands hold all {len(want)} of make -B's"
    mine = T._exec([os.path.join(root, "bin", "make"), "-n"], None, env, True, root, 300).out
    want = T._exec([sysmake, "-n"], None, env, True, root, 300).out
    if message(mine) != message(want):
        raise Fail(f"bin/make -n in the built project:\n{mine}\nthe system's make -n:\n{want}")
    return "make: the project is up to date for ours as for the system's"
