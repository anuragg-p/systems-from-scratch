"""xv6's own usertests against this track's kernel. Authors only: see README.md here.

    python3 tracks/xv6/tests/upstream/run.py [--core | --both] [--slow] [--keep-going]
                                             [--only NAME,...]

    (default)       the finished kernel (the core and every extension), quick set:
                    usertests -q, about 75s
    --core          the core-only kernel instead: the project at the last core lesson
    --both          the finished kernel, then the core-only one
    --slow          the slow tests too (usertests, no -q): about 4 minutes more per kernel
    --keep-going    usertests stops at its first failure; go on with the tests after it,
                    one `usertests NAME` each (slow: each one counts free memory twice)
    --only NAME,... just these tests, one `usertests NAME` each

The kernel is the project as the site shows it, written to tracks/xv6/build-upstream/<kernel>/
and built there with its own Makefile plus upstream.mk, which adds a disk image holding xv6's
usertests in place of the track's. Exit status 0 when every test that ran passed.

./learn test xv6 --ref runs the default (finished kernel, quick set) as part of the 07.03
check (tests/0703_utilities.py), through check().
"""

import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TRACK_DIR = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(os.path.dirname(TRACK_DIR))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from harness import core, timeline          # noqa: E402
from harness.core import Fail               # noqa: E402
from harness.session import Session         # noqa: E402

BUILD_DIR = os.path.join(TRACK_DIR, "build-upstream")
UPSTREAM_COMMIT = "7e95e76a19a7168c8db63f3ea40c6641f9ead93e"

# Tests that are not run, with why: features this kernel does not have. Empty: usertests.c is
# from before xv6 had lazy allocation, and every test in it passes on both kernels. A name here
# makes the run go one `usertests NAME` at a time, since usertests itself cannot leave one out.
SKIP = {}

# Seconds. BETWEEN: from one test's result to the next test's start, which takes in countfree()
# (it touches every free page, about 10s) at the start and the end of the run. QUICK and SLOW:
# one test, start to result; the slowest quick test (killstatus) takes about 10s, the slowest
# slow ones (badwrite, outofinodes) about 70s. A test still running after that is reported as
# hung and the run stops there.
BETWEEN = 180
QUICK = 90
SLOW = 600

EVENT = re.compile(r"test (\w+): "
                   r"|FAILED -- lost some free pages (\d+) \(out of (\d+)\)"
                   r"|(ALL TESTS PASSED|SOME TESTS FAILED)"
                   r"|(?<![A-Za-z0-9_])(OK|FAILED)\r?\n")


def tables():
    """{"quick": [names], "slow": [names]}, in the order usertests.c runs them."""
    with open(os.path.join(HERE, "usertests.c")) as f:
        src = f.read()
    out = {}
    for key, table in (("quick", "quicktests"), ("slow", "slowtests")):
        m = re.search(table + r"\[\]\s*=\s*\{(.*?)\n\};", src, re.S)
        if not m:
            raise Fail(f"no {table}[] in usertests.c")
        out[key] = re.findall(r'\{\s*\w+\s*,\s*"(\w+)"\s*\}', m.group(1))
    return out


def kernels(track):
    """kernel name -> the lesson its project is taken at (None: the end of the track)."""
    last_core = max((l.id for l in track.core_lessons), key=core.lesson_key)
    return {"finished": None, "core": last_core}


def prepare(track, name):
    """Write the project for kernel `name` to build-upstream/<name>/ and build its kernel and
    the usertests disk. Only files whose text changed are written, so make redoes only what
    changed. Returns the tree."""
    at = kernels(track)[name]
    dest = os.path.join(BUILD_DIR, name)
    proj = timeline.Project(track)
    want = set(proj.files_at(at))
    for dirpath, dirnames, filenames in os.walk(dest):
        if dirpath == dest:
            dirnames[:] = [d for d in dirnames if d != "build"]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            if os.path.relpath(full, dest).replace(os.sep, "/") not in want:
                os.unlink(full)
    for rel in sorted(want):
        data = proj.content(rel, at)
        target = os.path.join(dest, rel)
        try:
            with open(target, "rb") as f:
                if f.read() == data:
                    continue
        except OSError:
            pass
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as f:
            f.write(data)
        shutil.copymode(os.path.join(track.root, rel), target)
    argv = ["make", "-s", "-f", "Makefile", "-f", os.path.join(HERE, "upstream.mk"),
            f"UPSTREAM_DIR={HERE}", "build/kernel/kernel", "build/upstream/fs.img"]
    r = subprocess.run(argv, cwd=dest, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        raise Fail(f"building the {name} kernel for usertests failed:\n{r.stdout}{r.stderr}")
    return dest


def boot(track, tree, name, spawn):
    """The kernel in tree with the usertests disk, at its first shell prompt. snapshot=on: the
    image never changes, so every boot starts from the same files."""
    argv = track.module.run_argv(tree, display=["-display", "none"])
    image = os.path.join(tree, "build", "upstream", "fs.img")
    argv[argv.index("-drive") + 1] = f"file={image},if=none,format=raw,id=x0,snapshot=on"
    s = spawn(argv, name=name, fail_on=[r"panic: "])
    s.expect(r"init: starting sh", timeout=30)
    s.expect(r"\$ ", timeout=10)
    return s


class Result:
    def __init__(self, kernel, wanted, skipped=()):
        self.kernel = kernel
        self.wanted = wanted          # the tests to run, in order
        self.skipped = list(skipped)  # the tests SKIP leaves out
        self.tests = {}               # name -> (status, seconds, output): OK, FAILED, HUNG or PANIC
        self.problems = []            # what went wrong outside any one test (lost pages, a panic)
        self.seconds = 0.0

    @property
    def failed(self):
        return [n for n, (st, _, _) in self.tests.items() if st != "OK"]

    def not_run(self):
        return [n for n in self.wanted if n not in self.tests]

    def ok(self):
        return not self.failed and not self.problems and not self.not_run()

    def summary(self):
        passed = sum(1 for st, _, _ in self.tests.values() if st == "OK")
        return (f"{self.kernel}: {len(self.tests)} run, {passed} passed, {len(self.failed)} failed, "
                f"{len(self.skipped)} skipped, {len(self.not_run())} not run ({self.seconds:.0f}s)")


def drive(s, command, res, slow_names, log):
    """Type command (a usertests run) and read its report test by test into res. Returns
    False when the kernel panicked or a test hung: the machine is no use after that."""
    s.sendline(command)
    s.expect(re.escape(command) + r"\r?\n", timeout=10)
    current, started, timeout = None, 0.0, BETWEEN
    while True:
        try:
            m = s.expect(EVENT, timeout=timeout)
        except Fail as e:
            panic = None
            if "panic: " in s.output:
                try:                  # the rest of the panic's line
                    panic = s.expect(r"panic: [^\n]*\n", timeout=2, allow_fail=True)
                except Fail:
                    panic = re.search(r"panic: [^\n]*", s.output)
            what = panic.group(0).strip() if panic else str(e)
            if current:
                status = "PANIC" if panic else "HUNG"
                res.tests[current] = (status, time.monotonic() - started, s.tail(20))
                log(f"   {current:<16} {status}  {what}")
            res.problems.append(f"{what} (after `{command}`)")
            return False
        if m.group(1):
            current, started = m.group(1), time.monotonic()
            timeout = SLOW if current in slow_names else QUICK
        elif m.group(5):
            if current is None:
                res.problems.append(f"`{command}` printed {m.group(5)} outside any test")
                continue
            secs = time.monotonic() - started
            res.tests[current] = (m.group(5), secs, m.string[:m.start()])
            log(f"   {current:<16} {m.group(5):<6} {secs:5.1f}s")
            current, timeout = None, BETWEEN
        elif m.group(2):
            res.problems.append(f"lost free pages: {m.group(2)} free at the end, {m.group(3)} at the start "
                                f"(after `{command}`)")
            log(f"   {res.problems[-1]}")
            break                     # usertests exits after saying so
        else:
            break                     # ALL TESTS PASSED or SOME TESTS FAILED
    s.expect(r"\$ ", timeout=BETWEEN)
    return True


def run_kernel(track, name, slow=False, only=None, keep_going=False, spawn=Session, log=None):
    """Build kernel `name` ("finished" or "core"), boot it with the usertests disk, and run the
    quick set (with slow, everything). Returns a Result."""
    log = log or (lambda line: print(line, flush=True))
    t0 = time.monotonic()
    tree = prepare(track, name)
    names = tables()
    slow_names = set(names["slow"])
    wanted = names["quick"] + (names["slow"] if slow else [])
    if only:
        unknown = [n for n in only if n not in names["quick"] + names["slow"]]
        if unknown:
            raise Fail(f"usertests.c has no test named {', '.join(unknown)}")
        wanted = [n for n in names["quick"] + names["slow"] if n in only]
    skipped = [n for n in wanted if n in SKIP]
    wanted = [n for n in wanted if n not in SKIP]
    res = Result(name, wanted, skipped)
    one_by_one = bool(only or skipped)
    command = "usertests" if slow else "usertests -q"
    log(f"{name} kernel ({os.path.relpath(tree, ROOT)}): "
        + ("one `usertests NAME` per test" if one_by_one else f"`{command}`"))
    for n in skipped:
        log(f"   {n:<16} skipped: {SKIP[n]}")
    boots = 1
    s = boot(track, tree, f"{name}-1", spawn)
    if not one_by_one:
        if not drive(s, command, res, slow_names, log):
            s.close()
            s = None
        one_by_one = keep_going
    if one_by_one:
        for n in res.not_run():
            if s is None:             # after a panic or a hang: a fresh machine
                boots += 1
                s = boot(track, tree, f"{name}-{boots}", spawn)
            if not drive(s, f"usertests {n}", res, slow_names, log):
                s.close()
                s = None
    if s is not None:
        s.close()
    res.seconds = time.monotonic() - t0
    return res


def check(t):
    """For tests/0703_utilities.py: the quick set on the finished kernel, or Fail naming every
    test that failed. Only on the track's own code (./learn test --ref): a learner's workspace
    or a cut-out copy is not what build-upstream/ is built from."""
    if os.path.realpath(t.root) != os.path.realpath(TRACK_DIR):
        return None
    track = core.Track(os.path.basename(TRACK_DIR))
    res = run_kernel(track, "finished", spawn=t.spawn, log=lambda line: None)
    if not res.ok():
        lines = [f"xv6's usertests (tests/upstream): {res.summary()}"]
        lines += [f"  {n}: {res.tests[n][0]}\n" + "\n".join("    " + l for l in res.tests[n][2].strip().splitlines()[-8:])
                  for n in res.failed]
        lines += [f"  {p}" for p in res.problems]
        if res.not_run():
            lines.append(f"  not run: {' '.join(res.not_run())}\n  (usertests stops at its first failure; "
                         f"python3 tracks/xv6/tests/upstream/run.py --keep-going runs the rest)")
        raise Fail("\n".join(lines))
    return res


def main(argv):
    args = list(argv)
    usage = "usage: run.py [--core | --both] [--slow] [--keep-going] [--only NAME,...]"
    only = None
    if "--only" in args:
        i = args.index("--only")
        if i + 1 >= len(args):
            sys.exit(usage)
        only = [n for n in args[i + 1].split(",") if n]
        del args[i:i + 2]
    if set(args) - {"--core", "--both", "--slow", "--keep-going"}:
        sys.exit(usage)
    which = ["finished", "core"] if "--both" in args else ["core"] if "--core" in args else ["finished"]
    track = core.Track(os.path.basename(TRACK_DIR))
    print(f"xv6's usertests (xv6-riscv {UPSTREAM_COMMIT[:12]}) against this track's kernel", flush=True)
    bad = 0
    for name in which:
        try:
            res = run_kernel(track, name, slow="--slow" in args, only=only, keep_going="--keep-going" in args)
        except Fail as e:
            print(f"{name}: {e}")
            bad += 1
            continue
        for p in res.problems:
            print(f"   problem: {p}")
        if res.failed:
            print(f"   failed: {' '.join(res.failed)}")
        if res.not_run():
            print(f"   not run: {' '.join(res.not_run())}")
        print(res.summary())
        bad += not res.ok()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
