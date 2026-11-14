"""Tracks, lessons, and the test runner - the part every track shares.

A track is one system built from scratch (a kernel, a compiler, an
interpreter...). It lives in tracks/<id>/ and follows one contract:

    tracks/<id>/track.py                      TITLE, KIND, SUMMARY, build(t), fixtures
    tracks/<id>/lessons/NN-slug/README.md     module header (id, title, optional)
    tracks/<id>/lessons/NN-slug/NN.LL-slug.md one lesson, with a header block
    tracks/<id>/tests/NNLL_slug.py            def test(t): ... for lesson NN.LL

Nothing in this file knows what a kernel is.
"""

import datetime
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# LEARN_TRACKS_DIR points the tools at another set of tracks (the web tests use it).
TRACKS_DIR = os.environ.get("LEARN_TRACKS_DIR") or os.path.join(ROOT, "tracks")


class Fail(Exception):
    """A test failed. The message should say what was expected."""


# ---------------------------------------------------------------- metadata

def read_header(path):
    """Parse the '---' delimited key: value block at the top of a .md file."""
    meta = {}
    with open(path) as f:
        lines = f.read().splitlines()
    if not lines or lines[0].strip() != "---":
        return meta
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta


def lesson_key(lesson_id):
    """'02.03' -> (2, 3), so ids sort numerically."""
    return tuple(int(x) for x in lesson_id.split("."))


def module_id(lesson_id):
    """'08.02' -> '08'."""
    return lesson_id.split(".")[0]


def is_true(value):
    """A front matter flag: 'true' or 'yes', in any case. Anything else is false."""
    return (value or "").strip().lower() in ("true", "yes")


class Module:
    """One module, lessons/NN-slug/. `optional: true` in its README.md front matter makes it
    an extension: a learner opts into it after the core, and it stands apart from the others."""

    def __init__(self, module_id, title, optional=False):
        self.id = module_id
        self.title = title
        self.optional = optional


class Lesson:
    def __init__(self, track, lesson_id, title, module, doc=None, test=None, labels=(), optional=False):
        self.track = track
        self.id = lesson_id
        self.title = title
        self.module = module          # (module id, module title)
        self.doc = doc                # path to the .md, or None
        self.test = test              # path to the test .py, or None
        self.labels = list(labels)
        self.optional = optional      # its module is an optional extension

    @property
    def qualified(self):
        return f"{self.track.id}/{self.id}"


class Track:
    def __init__(self, track_id):
        self.id = track_id
        self.root = os.path.join(TRACKS_DIR, track_id)
        self._module = None
        self.modules = {}             # module id -> Module, filled by _discover
        self.lessons = self._discover()

    @property
    def module(self):
        """The track's track.py, imported once."""
        if self._module is None:
            path = os.path.join(self.root, "track.py")
            spec = importlib.util.spec_from_file_location(f"track_{self.id}", path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod
            spec.loader.exec_module(mod)
            self._module = mod
        return self._module

    @property
    def title(self):
        return getattr(self.module, "TITLE", self.id)

    @property
    def kind(self):
        return getattr(self.module, "KIND", "")

    def is_optional(self, some_id):
        """Is this lesson ('08.02') or module ('08') part of an optional extension?"""
        m = self.modules.get(module_id(some_id or ""))
        return bool(m and m.optional)

    @property
    def core_lessons(self):
        return [l for l in self.lessons if not l.optional]

    @property
    def optional_modules(self):
        """Optional modules that have at least one lesson, in order."""
        have = {l.module[0] for l in self.lessons}
        return [m for mid, m in sorted(self.modules.items()) if m.optional and mid in have]

    def _discover(self):
        lessons = {}
        modules = {}
        ldir = os.path.join(self.root, "lessons")
        if os.path.isdir(ldir):
            for mdir in sorted(os.listdir(ldir)):
                mpath = os.path.join(ldir, mdir)
                m = re.match(r"(\d\d)-(.+)", mdir)
                if not m or not os.path.isdir(mpath):
                    continue
                head = os.path.join(mpath, "README.md")
                mtitle = m.group(2).replace("-", " ").capitalize()
                mhead = read_header(head) if os.path.exists(head) else {}
                mtitle = mhead.get("title", mtitle)
                modules[m.group(1)] = Module(m.group(1), mtitle, is_true(mhead.get("optional")))
                for fname in sorted(os.listdir(mpath)):
                    fm = re.match(r"(\d\d\.\d\d)-.+\.md$", fname)
                    if not fm:
                        continue
                    path = os.path.join(mpath, fname)
                    meta = read_header(path)
                    lid = meta.get("id", fm.group(1))
                    labels = [x.strip() for x in meta.get("labels", "").split(",") if x.strip()]
                    lessons[lid] = Lesson(self, lid, meta.get("title", fname), (m.group(1), mtitle),
                                          doc=path, labels=labels, optional=modules[m.group(1)].optional)
        tdir = os.path.join(self.root, "tests")
        if os.path.isdir(tdir):
            for fname in sorted(os.listdir(tdir)):
                tm = re.match(r"(\d\d)(\d\d)_.+\.py$", fname)
                if not tm:
                    continue
                lid = f"{tm.group(1)}.{tm.group(2)}"
                path = os.path.join(tdir, fname)
                if lid in lessons:
                    lessons[lid].test = path
                else:
                    title = _docstring_title(path) or fname
                    mid = tm.group(1)
                    mod = modules.get(mid)
                    lessons[lid] = Lesson(self, lid, title, (mid, mod.title if mod else f"Module {mid}"), test=path,
                                          optional=bool(mod and mod.optional))
        self.modules = modules
        return sorted(lessons.values(), key=lambda l: lesson_key(l.id))


def _docstring_title(path):
    with open(path) as f:
        src = f.read()
    m = re.match(r'\s*"""\s*\d\d\.\d\d\s+(.+?)\s*$', src, re.M)
    return m.group(1).rstrip('"').strip() if m else None


def discover_tracks():
    if not os.path.isdir(TRACKS_DIR):
        return []
    return [Track(d) for d in sorted(os.listdir(TRACKS_DIR))
            if os.path.exists(os.path.join(TRACKS_DIR, d, "track.py"))]


# ---------------------------------------------------------------- running

class TestContext:
    """What a test function receives as `t`.

    t.track    the track's track.py module (its fixtures live there)
    t.root     the tree under test: the learner's workspace (work/<id>/)
               if one exists, otherwise the track's reference code
    t.tmp      a scratch directory, deleted after the test
    t.spawn()  start a Session that is closed automatically
    t.run()    run a command to completion, raising Fail on error
    t.check()  assert with a readable message
    """

    def __init__(self, track, lesson, root=None):
        self.track = track.module
        self.root = root or track.root
        self.lesson = lesson
        self.tmp = tempfile.mkdtemp(prefix=f"learn-{track.id}-{lesson.id}-")
        self.sessions = []

    def spawn(self, argv, **kw):
        from harness.session import Session
        s = Session(argv, **kw)
        self.sessions.append(s)
        return s

    def run(self, argv, cwd=None, check=True, timeout=600, env=None):
        r = subprocess.run(argv, cwd=cwd or self.root, capture_output=True, text=True,
                           timeout=timeout, env=env)
        if check and r.returncode != 0:
            raise Fail(f"command failed ({r.returncode}): {' '.join(argv)}\n{r.stdout}{r.stderr}")
        return r

    def check(self, cond, message):
        if not cond:
            raise Fail(message)

    def cleanup(self):
        for s in self.sessions:
            s.close()
        shutil.rmtree(self.tmp, ignore_errors=True)


def load_test(path):
    name = "test_" + os.path.basename(path)[:-3]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def record_result(track, lesson_id, ok, seconds, root=None):
    """Merge one result into <tree>/.test-logs/results.json."""
    path = os.path.join(root or track.root, ".test-logs", "results.json")
    try:
        with open(path) as f:
            results = json.load(f)
        if not isinstance(results, dict):
            results = {}
    except (OSError, ValueError):
        results = {}
    results[lesson_id] = {"ok": ok, "seconds": round(seconds, 2),
                          "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(results, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def run_lesson(track, lesson, root=None):
    """Run one lesson's test against root (default: the reference code).
    Returns (ok, seconds, report)."""
    t = TestContext(track, lesson, root)
    start = time.monotonic()
    report = ""
    ok = True
    try:
        load_test(lesson.test).test(t)
    except Fail as e:
        ok = False
        report = str(e)
    except Exception:
        ok = False
        report = traceback.format_exc()
    if not ok:
        for s in t.sessions:
            report += f"\n--- last lines from {s.name} ---\n{s.tail(15)}"
    logdir = os.path.join(t.root, ".test-logs")
    os.makedirs(logdir, exist_ok=True)
    with open(os.path.join(logdir, f"{lesson.id}.log"), "w") as f:
        for s in t.sessions:
            f.write(f"=== {s.name}: {' '.join(s.argv)}\n{s.output}\n")
    t.cleanup()
    seconds = time.monotonic() - start
    record_result(track, lesson.id, ok, seconds, t.root)
    return ok, seconds, report


def select_lessons(track, patterns):
    if not patterns:
        return [l for l in track.lessons if l.test]
    picked = []
    for l in track.lessons:
        if l.test and any(l.id.startswith(p) or l.id.replace(".", "").startswith(p) for p in patterns):
            picked.append(l)
    return picked


def run_tests(tracks, patterns, verbose=False, roots=None):
    """roots maps a track id to the tree to test (a learner workspace)."""
    failed = []
    total = 0
    roots = roots or {}
    for track in tracks:
        root = roots.get(track.id)
        lessons = select_lessons(track, patterns)
        if not lessons:
            continue
        where = f"  [your workspace: {os.path.relpath(root, ROOT)}]" if root else ""
        print(f"== {track.id}: {track.title}{where}")
        build = getattr(track.module, "build", None)
        if build:
            t0 = time.monotonic()
            try:
                build(TestContext(track, Lesson(track, "00.00", "build", ("00", "build")), root))
            except Fail as e:
                print(f"   BUILD FAILED\n{e}")
                failed.append(f"{track.id}/build")
                continue
            print(f"   built in {time.monotonic() - t0:.1f}s")
        width = max(len(l.title) for l in lessons) + 2
        for l in lessons:
            total += 1
            ok, secs, report = run_lesson(track, l, root)
            status = "PASS" if ok else "FAIL"
            print(f"   {l.id}  {l.title.ljust(width, '.')} {status} {secs:4.1f}s", flush=True)
            if not ok:
                failed.append(l.qualified)
                print("      " + report.replace("\n", "\n      "))
    print()
    if failed:
        print(f"{len(failed)} of {total} failed: {' '.join(failed)}")
        return 1
    print(f"all {total} passed")
    return 0
