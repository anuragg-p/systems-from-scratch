"""The `learn` command.

    ./learn                         the map of every track
    ./learn map [track]             same, for one track
    ./learn map --write             rewrite the map in README.md
    ./learn start <track> [--at NN.LL] [--force]
                                    make your workspace, work/<track>/, and cut out
                                    the first lesson for you to build
    ./learn status [track]          which lesson you are on and where its TODOs are
    ./learn next <track> [--use-solution]
                                    move on: cut out the next lesson for you to build
                                    (--use-solution fills the current one with the
                                    reference code instead of yours). It stops at the
                                    end of the core, and at the end of an extension
    ./learn extend <track> <NN> [--fill-core]
                                    start optional module NN (an extension) once the
                                    core is built; --fill-core first fills every core
                                    lesson you have not built with the reference code
    ./learn solution <track> <id>   show the reference code for a lesson
    ./learn run <track> [--at NN.LL] [--fresh] [-- args...]
                                    build the system as it stands at lesson NN.LL and
                                    run it (without --at: the finished system). Its
                                    files are written to build/at/<track>/NN.LL/
                                    (build/at/<track>/finished/) for you to open and
                                    change: your edits there stay until the track's
                                    code itself changes; --fresh writes them again.
                                    args after -- go to the program, such as a file
                                    and a statement for db:
                                      ./learn run db --at 04.02 -- demo.db "SELECT 1;"
    ./learn bench <track> [--at NN.LL] [--fresh] [args...]
                                    the same build, then the track's benchmark on it
                                    (args go to the benchmark)
    ./learn files <track> [--at NN.LL] [dir]
                                    write the project as it stands at lesson NN.LL
                                    to dir (default: where run puts it); build nothing

  For authors (tests are internal: they verify the reference code works):
    ./learn test [track] [ids...] [--ref]
                                    run lesson tests (ids are prefixes: 02, 02.03)
    ./learn check-skeleton <track> [ids...]
                                    cutting each lesson out still builds, and that
                                    lesson's test then fails
    ./learn new <track> <id> <title...>
                                    scaffold a lesson doc and its test
    ./learn new-track <id> <kind> <title...>
                                    scaffold a new track (kernel, compiler, interpreter, ...)
    ./learn serve [--port N]        local web UI on 127.0.0.1 (default port 8000)
    ./learn export <outdir>         the site as plain files for a static host (Vercel):
                                    every page, asset and Files view (harness/web/export.py)
    ./learn selftest               run the harness's own tests (harness/tests)
    ./learn check                   every lesson has a doc and a test; every figure a
                                    doc names exists; every file has a lesson it comes
                                    with (FILES_FROM in track.py, or its first region);
                                    outlines follow templates/outline.md; text is ASCII;
                                    and verify's static checks (no builds) on every lesson
                                    not listed in tracks/<id>/lessons/verify-pending.txt
    ./learn verify [track] [ids...] [--jobs N] [--fresh] [--static] [--report]
                   [--allow-missing] [--keep]
                                    what each lesson says is what its project does: quoted
                                    code exists at that lesson, and every annotated transcript,
                                    patch and fact is replayed and compared (harness/verify.py;
                                    the annotations: README.md, "Verifying a lesson")
"""

import fnmatch
import hashlib
import inspect
import os
import re
import shutil
import subprocess
import sys

from harness.core import (ROOT, TRACKS_DIR, Fail, Lesson, TestContext, discover_tracks,
                          lesson_key, run_lesson, run_tests, Track)
from harness import workspace as ws

MAP_START = "<!-- map:start -->"
MAP_END = "<!-- map:end -->"


def by_id(tracks, track_id):
    for t in tracks:
        if t.id == track_id:
            return t
    sys.exit(f"no track named {track_id!r}; have: {', '.join(t.id for t in tracks)}")


# ---------------------------------------------------------------- map

def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def lesson_count(tr):
    """'33 lessons', with extensions mentioned separately: '33 lessons, +2 optional modules'."""
    text = plural(len(tr.core_lessons), "lesson")
    n = len(tr.optional_modules)
    return text + (f", +{plural(n, 'optional module')}" if n else "")


def cmd_map(args):
    tracks = discover_tracks()
    if "--write" in args:
        write_map(tracks)
        return 0
    if args:
        tracks = [by_id(tracks, args[0])]
    for tr in tracks:
        print(f"{tr.id} - {tr.title}  [{tr.kind}]  {lesson_count(tr)}")
        mod = None
        for part in (tr.core_lessons, [l for l in tr.lessons if l.optional]):
            if part and part[0].optional:
                print("\n  Extensions - optional, each independent of the others: ./learn extend "
                      f"{tr.id} <NN> once the core is built")
            for l in part:
                if l.module != mod:
                    mod = l.module
                    print(f"\n  Module {mod[0]} - {mod[1]}" + ("  (optional)" if l.optional else ""))
                have = ("doc " if l.doc else "--- ") + ("test" if l.test else "----")
                labels = ", ".join(l.labels)
                print(f"    {l.id}  {l.title:<44} {labels:<24} {have}")
        print()
    return 0


def map_markdown(tracks):
    out = []
    for tr in tracks:
        out.append(f"### {tr.title}\n")
        out.append(f"Track `{tr.id}` - kind: {tr.kind} - {lesson_count(tr)} - on the site: `./learn serve`, then /t/{tr.id}\n")
        mod = None
        for part in (tr.core_lessons, [l for l in tr.lessons if l.optional]):
            if part and part[0].optional:
                out.append("\n**Extensions** - optional modules, each independent of the others, "
                           "each built on the finished core\n")
            for l in part:
                if l.module != mod:
                    mod = l.module
                    out.append(f"\n**Module {mod[0]} - {mod[1]}**" + (" (optional)" if l.optional else "") + "\n")
                name = l.title
                if l.doc:
                    name = f"[{l.title}]({os.path.relpath(l.doc, ROOT)})"
                labels = f" - {', '.join(l.labels)}" if l.labels else ""
                out.append(f"- {l.id} {name}{labels}")
        out.append("")
    return "\n".join(out)


def write_map(tracks):
    path = os.path.join(ROOT, "README.md")
    with open(path) as f:
        text = f.read()
    if MAP_START not in text or MAP_END not in text:
        sys.exit(f"README.md needs {MAP_START} and {MAP_END} markers")
    head, rest = text.split(MAP_START, 1)
    _, tail = rest.split(MAP_END, 1)
    with open(path, "w") as f:
        f.write(head + MAP_START + "\n" + map_markdown(tracks) + "\n" + MAP_END + tail)
    print("README.md map updated")


# ---------------------------------------------------------------- test

def cmd_test(args):
    tracks = discover_tracks()
    ref = "--ref" in args
    args = [a for a in args if a != "--ref"]
    if args and not re.match(r"^\d", args[0]):
        tracks = [by_id(tracks, args[0])]
        args = args[1:]
    roots = {}
    if not ref:
        for tr in tracks:
            state = ws.load_state(tr)
            if state is None:
                continue
            roots[tr.id] = ws.work_root(tr)
            if not args and state.get("current"):
                # In a workspace, "test everything" means everything up to
                # the lesson you are on, on its own path: the core lessons, plus
                # the earlier lessons of the extension you are in.
                cur = state["current"]
                args_for = [l.id for l in tr.lessons if l.test and (l.id == cur or ws.position(tr, state, l.id) == "behind")]
                return run_tests([tr], args_for, roots=roots)
    return run_tests(tracks, args, roots=roots)


# ---------------------------------------------------------------- building it yourself

def lesson_named(track, lid):
    for l in track.lessons:
        if l.id == lid:
            return l
    return None


def print_todos(track, lid, changed):
    l = lesson_named(track, lid)
    title = l.title if l else ""
    print(f"\nLesson {lid} {title}")
    if l and l.doc:
        print(f"  read:   {os.path.relpath(l.doc, ROOT)}")
    print("  build:")
    root = ws.work_root(track)
    for rel, r in changed:
        print(f"    {os.path.relpath(os.path.join(root, rel), ROOT)}:{r.line}  {r.title}")
    # No "run it" line: ./learn run builds the track's own code at a lesson, not this workspace.
    print(f"  then:   ./learn next {track.id}")


def cmd_start(args):
    if not args:
        sys.exit("usage: learn start <track> [--at NN.LL] [--force]")
    track = by_id(discover_tracks(), args[0])
    at = args[args.index("--at") + 1] if "--at" in args else None
    try:
        cur, changed = ws.start(track, at=at, force="--force" in args)
    except Fail as e:
        sys.exit(str(e))
    print(f"Your workspace is {os.path.relpath(ws.work_root(track), ROOT)}/ - a full copy of the track,")
    print("with the code of the lesson you are on cut out. Everything else works,")
    print("so you can build and run the system while you fill in the hole.")
    print_todos(track, cur, changed)
    return 0


def extension_hint(track, prog):
    """Lines naming the extensions still open to start, or [] when there are none."""
    left = [e for e in prog["extensions"] if not e["complete"] and e["total"]]
    if not left:
        return []
    return ["Optional extensions, each independent of the others:"] + \
        [f"  ./learn extend {track.id} {e['id']}    {e['title']} ({plural(e['total'], 'lesson')})" for e in left]


def cmd_status(args):
    tracks = discover_tracks()
    if args:
        tracks = [by_id(tracks, args[0])]
    any_ws = False
    for tr in tracks:
        state = ws.load_state(tr)
        if state is None:
            continue
        any_ws = True
        prog = ws.progress(tr, state)
        core = prog["core"]
        word = "core lessons" if prog["extensions"] else "lessons"
        print(f"{tr.id}: {core['done']} of {core['total']} {word} built")
        for e in prog["extensions"]:
            if e["started"]:
                print(f"  extension {e['id']} {e['title']}: {e['done']} of {e['total']} built")
        cur = state.get("current")
        if not cur:
            if prog["stage"] == "idle":
                print(f"  no lesson in progress; core lessons not built: {' '.join(core['left'])}")
            else:
                print("  all done - every core lesson is your own code now" if prog["extensions"]
                      else "  all done - every lesson is your own code now")
            for line in extension_hint(tr, prog):
                print("  " + line)
            continue
        regions = [r for r in ws.scan_tree(tr.module, ws.work_root(tr)) if r.lesson == cur]
        print_todos(tr, cur, [(r.path, r) for r in regions])
    if not any_ws:
        print("no workspace yet: ./learn start <track>")
    return 0


def cmd_next(args):
    if not args:
        sys.exit("usage: learn next <track> [--use-solution]")
    track = by_id(discover_tracks(), args[0])
    state = ws.load_state(track)
    if state is None:
        sys.exit(f"no workspace yet: ./learn start {track.id}")
    cur = state.get("current")
    if not cur:
        print("no lesson in progress: the core is built" if track.optional_modules else "every lesson is already built")
        for line in extension_hint(track, ws.progress(track, state)):
            print(line)
        return 0
    try:
        nxt, changed = ws.advance(track, use_solution="--use-solution" in args)
    except Fail as e:
        sys.exit(str(e))
    if nxt is None:
        prog = ws.progress(track, ws.load_state(track))
        if track.is_optional(cur):
            mod = track.modules[cur.split(".")[0]]
            print(f"That was the last lesson of extension {mod.id} {mod.title}. It is your code now.")
        elif track.optional_modules:
            print("That was the last core lesson. The whole core is your code now.")
        else:
            print("That was the last lesson. The whole system is your code now.")
        for line in extension_hint(track, prog):
            print(line)
        return 0
    print_todos(track, nxt, changed)
    return 0


def cmd_extend(args):
    pos = [a for a in args if not a.startswith("--")]
    if len(pos) != 2 or not re.match(r"^\d\d$", pos[1]) or set(args) - set(pos) - {"--fill-core"}:
        sys.exit("usage: learn extend <track> <NN> [--fill-core]")
    track = by_id(discover_tracks(), pos[0])
    try:
        cur, changed = ws.extend(track, pos[1], fill_core="--fill-core" in args)
    except Fail as e:
        sys.exit(str(e))
    mod = track.modules[pos[1]]
    print(f"Extension {mod.id} {mod.title}: optional, and independent of the other extensions.")
    if "--fill-core" in args:
        print("Every core lesson you had not built now holds the reference code.")
    print_todos(track, cur, changed)
    return 0


# ---------------------------------------------------------------- run it, as it stands at a lesson
#
# run, bench and files write the project as the site shows it at a lesson (timeline.py's
# materialize) into build/at/<track>/<NN.LL>/, or the finished track into .../finished/, and
# build and run it there. Never in work/ or tracks/. The directory is written again only when
# the track's own files change (STAMP holds what they were), or with --fresh, so what a reader
# edits there to try something stays until then.

STAMP = ".learn-at"


def build_root():
    """Where projects are written to be built: build/ at the top ($LEARN_BUILD_DIR overrides it)."""
    return os.environ.get("LEARN_BUILD_DIR") or os.path.join(ROOT, "build")


def run_options(args, usage, loose=False):
    """`<track> [--at NN.LL] [--fresh] [args...] [-- args...]` -> (track id, at, fresh, args).
    --ref is accepted and means nothing (the finished track is what runs without --at). Options
    it does not know are an error, or with loose=True (bench) arguments for the program."""
    after = []
    if "--" in args:
        i = args.index("--")
        args, after = args[:i], args[i + 1:]
    tid, at, fresh, extra = None, None, False, []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--at":
            if i + 1 >= len(args):
                sys.exit(usage)
            at = args[i + 1]
            i += 2
            continue
        if a.startswith("--at="):
            at = a[len("--at="):]
        elif a == "--fresh":
            fresh = True
        elif a == "--ref":
            pass
        elif tid is None and not a.startswith("-"):
            tid = a
        elif a.startswith("-") and not loose:
            sys.exit(usage)
        else:
            extra.append(a)
        i += 1
    if tid is None:
        sys.exit(usage)
    return tid, at, fresh, extra + after


def _inside(path, top):
    path, top = os.path.realpath(path), os.path.realpath(top)
    return path == top or path.startswith(top + os.sep)


def _has_code(track, proj, at):
    patterns = getattr(track.module, "SOURCES", ["*"])
    return any(fnmatch.fnmatch(rel, p) for rel in proj.files_at(at) for p in patterns)


def _sources_stamp(track, proj, at):
    """What the project at `at` is written from: the track's files and the code that writes it."""
    from harness import timeline
    paths = sorted([os.path.join(track.root, f) for f in proj.files] +
                   [os.path.join(track.root, "track.py"), timeline.__file__, ws.__file__])
    h = hashlib.sha256(f"{track.id} {at or 'finished'}\n".encode())
    for p in paths:
        try:
            st = os.stat(p)
        except OSError:
            continue
        h.update(f"{p} {st.st_mtime_ns} {st.st_size}\n".encode())
    return h.hexdigest()


def project_dir(track, at=None, fresh=False, dest=None, need_code=True, top=None):
    """The project as it stands at lesson `at` (None: the finished track), written to dest
    (default <top>/at/<track>/<at or finished>/, top defaulting to build_root()). Returns (dest,
    what it is: "db as it stands at 04.02 (WHERE and expressions)", whether it was written now).
    Exits with one line for a lesson that is not in the track, or (need_code) whose project has
    no code to build yet."""
    from harness import timeline
    proj = timeline.Project(track)
    if at is None:
        what = f"the finished {track.id}"
    else:
        if not re.match(r"^\d\d\.\d\d$", at):
            sys.exit(f"--at takes a lesson number such as 02.03, not {at!r}")
        if at not in {l.id for l in track.lessons} | proj.lesson_ids():
            sys.exit(f"track {track.id} has no lesson {at}")
        l = lesson_named(track, at)
        what = f"{track.id} as it stands at {at}" + (f" ({l.title})" if l else "")
        if need_code and not _has_code(track, proj, at):
            first = next((x.id for x in track.core_lessons if _has_code(track, proj, x.id)), None)
            sys.exit(f"{track.id} has no code yet at {at}, so there is nothing to build or run"
                     + (f"; the code starts at {first}" if first else ""))
    mine = dest is None
    if mine:
        dest = os.path.join(top or build_root(), "at", track.id, at or "finished")
    from harness import core
    for top in (ws.WORK_DIR, os.path.join(ROOT, "work"), core.TRACKS_DIR, os.path.join(ROOT, "tracks")):
        if _inside(dest, top):
            sys.exit(f"will not write into {os.path.relpath(top, ROOT)}/: pick a directory outside it")
    stamp = _sources_stamp(track, proj, at)
    stamp_file = os.path.join(dest, STAMP)
    if mine and not fresh:
        try:
            with open(stamp_file) as f:
                if f.read().strip() == stamp:
                    return dest, what, False
        except OSError:
            pass
    if mine:
        shutil.rmtree(dest, ignore_errors=True)
    elif os.path.isdir(dest) and os.listdir(dest):
        sys.exit(f"{dest} is not empty: pick a new directory")
    os.makedirs(dest, exist_ok=True)
    proj.materialize(at, dest)
    if mine:
        with open(stamp_file, "w") as f:      # last: a write cut short is done again next time
            f.write(stamp + "\n")
    return dest, what, True


# Paths run, bench and files print are relative to this: the checkout (./learn verify replays
# them in a copy of its layout, harness/verify.py, and sets it there, with a RUN_HOOK that marks
# the moment the system starts, after its build).
SHOWN_FROM = ROOT
RUN_HOOK = None


def _shown(path):
    rel = os.path.relpath(path, SHOWN_FROM)
    return (path if rel.startswith("..") else rel).rstrip(os.sep) + "/"


def _build(track, root):
    if hasattr(track.module, "prepare"):
        # prepare(root) returns the build command for this tree, or None.
        argv = track.module.prepare(root)
        if argv and _call(argv, root) != 0:
            sys.exit("build failed")


def _call(argv, cwd):
    """Run a program in this terminal until it exits. Control-C goes to it, and it decides."""
    try:
        p = subprocess.Popen(argv, cwd=cwd)
    except OSError as e:
        sys.exit(f"cannot start {argv[0]}: {e.strerror or e}")
    while True:
        try:
            return p.wait()
        except KeyboardInterrupt:
            continue


def _takes_args(fn):
    try:
        return "args" in inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False


def cmd_run(args):
    usage = "usage: learn run <track> [--at NN.LL] [--fresh] [-- args...]"
    if not args:
        sys.exit(usage)
    tid, at, fresh, extra = run_options(args, usage)
    track = by_id(discover_tracks(), tid)
    mod = track.module
    if not hasattr(mod, "run_argv"):
        sys.exit(f"track {track.id} does not say how to run it (no run_argv in track.py)")
    if extra and not _takes_args(mod.run_argv):
        sys.exit(f"./learn run {track.id} takes no arguments for the program")
    root, what, _ = project_dir(track, at, fresh)
    print(f"Running {what}. Its files are in {_shown(root)}", flush=True)
    _build(track, root)
    if RUN_HOOK:
        RUN_HOOK()
    return _call(mod.run_argv(root, args=extra) if extra else mod.run_argv(root), root)


def cmd_bench(args):
    """Run the track's benchmark: track.py's bench(root) gives the command, run on the project
    at a lesson (or the finished track) after building it; other args go to the benchmark."""
    usage = "usage: learn bench <track> [--at NN.LL] [--fresh] [args...]"
    if not args:
        sys.exit(usage)
    tid, at, fresh, extra = run_options(args, usage, loose=True)
    track = by_id(discover_tracks(), tid)
    hook = getattr(track.module, "bench", None)
    if not callable(hook):
        sys.exit(f"track {track.id} has no benchmark (no bench(root) in track.py)")
    root, what, _ = project_dir(track, at, fresh)
    print(f"Benchmarking {what}. Its files are in {_shown(root)}", flush=True)
    _build(track, root)
    if RUN_HOOK:
        RUN_HOOK()
    return _call(list(hook(root)) + extra, root)


def cmd_files(args):
    """Write the project at a lesson to a directory, and build nothing."""
    usage = "usage: learn files <track> [--at NN.LL] [dir]"
    if not args:
        sys.exit(usage)
    tid, at, fresh, extra = run_options(args, usage)
    if len(extra) > 1:
        sys.exit(usage)
    track = by_id(discover_tracks(), tid)
    root, what, wrote = project_dir(track, at, fresh, dest=os.path.abspath(extra[0]) if extra else None,
                                    need_code=False)
    print(f"Wrote {what} to {_shown(root)}" if wrote else f"{what} is already in {_shown(root)}")
    return 0


def cmd_solution(args):
    if len(args) < 2:
        sys.exit("usage: learn solution <track> <NN.LL>")
    track = by_id(discover_tracks(), args[0])
    regions = [r for r in ws.scan_tree(track.module, track.root) if r.lesson == args[1]]
    if not regions:
        sys.exit(f"lesson {args[1]} builds nothing in track {track.id}")
    from harness import timeline
    for r in regions:
        code, head = ws.region_code(track.root, r)
        print(f"==> tracks/{track.id}/{r.path}:{r.line}  {r.title}")
        print("\n".join(head + timeline.unmarked(code)))
        print()
    return 0


def cmd_check_skeleton(args):
    import shutil
    import tempfile
    if not args:
        sys.exit("usage: learn check-skeleton <track> [ids...]")
    track = by_id(discover_tracks(), args[0])
    order = ws.lessons_with_regions(track.module, track.root)
    if args[1:]:
        order = [l for l in order if any(l.startswith(p) for p in args[1:])]
    bad = []
    for lid in order:
        tmp = tempfile.mkdtemp(prefix=f"skeleton-{track.id}-{lid}-")
        try:
            root = os.path.join(tmp, track.id)
            ws.copy_track(track, root)
            ws.cut(track.module, root, lid)
            lesson = lesson_named(track, lid) or Lesson(track, lid, "?", (lid[:2], ""))
            try:
                track.module.build(TestContext(track, lesson, root))
            except Fail as e:
                bad.append(lid)
                print(f"   {lid}  cut out: DOES NOT BUILD\n      " + str(e)[-600:].replace("\n", "\n      "))
                continue
            if not lesson.test:
                print(f"   {lid}  cut out: builds (no test to check)")
                continue
            ok, secs, report = run_lesson(track, lesson, root)
            if ok:
                bad.append(lid)
                print(f"   {lid}  cut out: builds, but its test still PASSES - the hole is invisible")
            else:
                print(f"   {lid}  cut out: builds, test fails as it should ({secs:.1f}s): {report.splitlines()[0][:90]}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\ncheck-skeleton:", "ok" if not bad else f"problems in {' '.join(bad)}")
    return 1 if bad else 0


# ---------------------------------------------------------------- the project at each lesson
#
# Internal, like check-skeleton, and left out of the help on purpose: learners never see it.
#
#   ./learn check-timeline <track> [ids...] [--no-boot] [--seconds N] [-j N] [--keep]
#
# For every lesson on its reading path (or those the ids pick, as prefixes), write the project
# as the site shows it at that lesson (harness/timeline.py) into a temporary directory, build
# it with the track's prepare(root), and boot it: track.py's timeline_run(root) (or
# run_argv(root)) started unattended, with the steps timeline_boot(lesson) gives - (text to
# type or None, regex to wait for) - and then a few quiet seconds in which none of
# TIMELINE_FAIL may show and the system must keep running. Once it is stopped, the optional
# timeline_after(root, lesson) checks what the run left behind (a track that writes files
# can have another program open them); it returns a short note, or raises Fail. A lesson
# whose project has no source file yet has nothing to build.

def timeline_lesson(track, proj, lid, boot=True, seconds=20, settle=2.0, keep=False):
    import shutil
    import subprocess
    import tempfile
    from harness.session import Session
    mod = track.module
    tmp = tempfile.mkdtemp(prefix=f"timeline-{track.id}-{lid}-")
    root = os.path.join(tmp, track.id)
    res = {"id": lid, "files": 0, "build": "-", "boot": "-", "note": "", "dir": tmp}
    try:
        res["files"] = len(proj.materialize(lid, root))
        if not ws.source_files(mod, root):
            res["note"] = "no source files yet: nothing to build"
            return res
        argv = mod.prepare(root) if hasattr(mod, "prepare") else None
        if argv:
            try:
                p = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=900)
            except subprocess.TimeoutExpired:
                res.update(build="FAIL", note="build timed out")
                return res
            if p.returncode != 0:
                out = [l.strip() for l in (p.stdout + p.stderr).splitlines() if l.strip()]
                errs = [l for l in out if re.search(r"error|undefined reference|No rule to make", l)]
                res.update(build="FAIL", note=(errs or out or ["(no output)"])[0][:200])
                return res
        res["build"] = "ok"
        run = getattr(mod, "timeline_run", None) or getattr(mod, "run_argv", None)
        if not boot or run is None:
            return res
        fails = list(getattr(mod, "TIMELINE_FAIL", []))
        steps = list(mod.timeline_boot(lid)) if hasattr(mod, "timeline_boot") else []
        try:
            s = Session(run(root), name=lid, cwd=root, fail_on=fails)
        except OSError as e:
            res.update(boot="FAIL", note=f"cannot start it: {e}")
            return res
        try:
            for send, expect in steps:
                if send is not None:
                    s.sendline(send)
                s.expect(expect, timeout=seconds)
            if fails:
                s.expect_absent("|".join(f"(?:{f})" for f in fails), within=settle)
            else:
                s.expect_absent(r"(?!)", within=settle)     # just let it run
            seen = [f for f in fails if re.search(f, s.output)]
            if seen:
                raise Fail(f"{lid}: saw {seen[0]!r}")
            if s.proc.poll() is not None:
                raise Fail(f"stopped running (exit {s.proc.returncode})")
            res["boot"] = "ok"
            typed = [send for send, _ in steps if send is not None]
            said = (f" (typed: {', '.join(typed)})" if len(typed) <= 3 else
                    f" (typed {len(typed)} lines, {typed[0]} ... {typed[-1]})")
            res["note"] = (f"{plural(len(steps), 'check')} ok" if steps else "runs") + \
                (said if typed else "") + "; "
        except Fail as e:
            res["boot"] = "FAIL"
            res["note"] = str(e)[:200] + " | "
        finally:
            s.close()
        after = getattr(mod, "timeline_after", None)
        if after and res["boot"] == "ok":
            try:
                got = after(root, lid)
                res["note"] += (got + "; ") if got else ""
            except Exception as e:    # Fail, or a bug in the hook: either way this lesson fails
                res["boot"] = "FAIL"
                why = str(e) if isinstance(e, Fail) else f"{type(e).__name__}: {e}"
                res["note"] += "after the run: " + why[:200] + " | "
        lines = [l.strip() for l in s.output.replace("\r", "").split("\n") if l.strip()]
        res["note"] += ("last line: " + lines[-1][:60]) if lines else "prints nothing"
        return res
    finally:
        if keep:
            print(f"   {lid}: kept {root}", flush=True)
        else:
            shutil.rmtree(tmp, ignore_errors=True)


def cmd_check_timeline(args):
    from concurrent.futures import ThreadPoolExecutor
    from harness import timeline
    pos = [a for a in args if not a.startswith("-")]
    opts = [a for a in args if a.startswith("-")]

    def opt(name, default):
        if name in args and args.index(name) + 1 < len(args):
            val = args[args.index(name) + 1]
            pos.remove(val)
            return val
        return default
    seconds, jobs = float(opt("--seconds", "20")), int(opt("-j", str(min(4, os.cpu_count() or 1))))
    if not pos or set(opts) - {"--no-boot", "--seconds", "-j", "--keep"}:
        sys.exit("usage: learn check-timeline <track> [ids...] [--no-boot] [--seconds N] [-j N] [--keep]")
    track = by_id(discover_tracks(), pos[0])
    proj = timeline.Project(track)
    ids = {l.id for l in track.lessons} | proj.lesson_ids()
    order = sorted((i for i in ids if not track.is_optional(i)), key=lesson_key) + \
        sorted((i for i in ids if track.is_optional(i)), key=lesson_key)
    if pos[1:]:
        order = [i for i in order if any(i.startswith(p) for p in pos[1:])]
    print(f"{track.id}: the project at {plural(len(order), 'lesson')}, built"
          + ("" if "--no-boot" in opts else " and booted"), flush=True)
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        futures = [pool.submit(timeline_lesson, track, proj, lid, "--no-boot" not in opts, seconds,
                               keep="--keep" in opts) for lid in order]
        results = []
        for f in futures:
            r = f.result()
            results.append(r)
            print(f"   {r['id']}  {r['files']:>4} files  build {r['build']:<4}  boot {r['boot']:<4}  {r['note']}",
                  flush=True)
    bad = [r["id"] for r in results if "FAIL" in (r["build"], r["boot"])]
    print("\ncheck-timeline:", "ok" if not bad else f"problems in {' '.join(bad)}")
    return 1 if bad else 0


# ---------------------------------------------------------------- scaffolding

def slugify(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def fill(template, **values):
    with open(os.path.join(ROOT, "templates", template)) as f:
        text = f.read()
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def cmd_new(args):
    if len(args) < 3 or not re.match(r"^\d\d\.\d\d$", args[1]):
        sys.exit("usage: learn new <track> <NN.LL> <title...>")
    track = by_id(discover_tracks(), args[0])
    lid, title = args[1], " ".join(args[2:])
    mid = lid[:2]
    ldir = os.path.join(track.root, "lessons")
    os.makedirs(ldir, exist_ok=True)
    mdirs = [d for d in os.listdir(ldir) if d.startswith(mid + "-")]
    if mdirs:
        mdir = os.path.join(ldir, mdirs[0])
    else:
        mdir = os.path.join(ldir, f"{mid}-module")
        os.makedirs(mdir)
        with open(os.path.join(mdir, "README.md"), "w") as f:
            f.write(fill("module.md", ID=mid, TITLE=f"Module {mid}"))
    slug = slugify(title)
    doc = os.path.join(mdir, f"{lid}-{slug}.md")
    test = os.path.join(track.root, "tests", f"{lid.replace('.', '')}_{slug.replace('-', '_')}.py")
    os.makedirs(os.path.dirname(test), exist_ok=True)
    for path, tpl in ((doc, "lesson.md"), (test, "test.py")):
        if os.path.exists(path):
            sys.exit(f"{path} already exists")
        with open(path, "w") as f:
            f.write(fill(tpl, ID=lid, TITLE=title, TEST=os.path.relpath(test, track.root), TRACK=track.id))
        print("created", os.path.relpath(path, ROOT))
    return 0


def cmd_new_track(args):
    if len(args) < 3:
        sys.exit("usage: learn new-track <id> <kind> <title...>")
    tid, kind, title = args[0], args[1], " ".join(args[2:])
    root = os.path.join(TRACKS_DIR, tid)
    if os.path.exists(root):
        sys.exit(f"{root} already exists")
    os.makedirs(os.path.join(root, "lessons"))
    os.makedirs(os.path.join(root, "tests"))
    with open(os.path.join(root, "track.py"), "w") as f:
        f.write(fill("track.py", ID=tid, KIND=kind, TITLE=title))
    print(f"created tracks/{tid}/ - next: ./learn new {tid} 00.01 <first lesson title>")
    return 0


# ---------------------------------------------------------------- check

TEXT_EXT = {".md", ".py", ".c", ".h", ".S", ".ld", ".pl", ".txt", ".svg", ""}
SKIP_DIRS = {".git", ".test-logs", "__pycache__"}


def cmd_check(args):
    from harness.web import art
    problems = []
    for tr in discover_tracks():
        seen = set()
        for l in tr.lessons:
            if l.id in seen:
                problems.append(f"{l.qualified}: duplicate lesson id")
            seen.add(l.id)
            if not l.doc:
                problems.append(f"{l.qualified}: test has no lesson doc")
            if not l.test:
                problems.append(f"{l.qualified}: lesson has no test")
            if l.doc:
                for n, what in art.figure_problems(l.doc):
                    problems.append(f"{os.path.relpath(l.doc, ROOT)}:{n}: {what}")
        from harness import timeline
        problems.extend(f"{tr.id}: {p}" for p in timeline.Project(tr).problems())
    from harness import verify
    found, notes = verify.static_problems()
    problems.extend(found)
    from harness import outlines
    track_ids = {t.id for t in discover_tracks()}
    for o in outlines.discover():
        problems.extend(outlines.problems(o))
        if o.id in track_ids:
            problems.append(f"{os.path.relpath(o.path, ROOT)}: id {o.id!r} is taken by tracks/{o.id}, so the site shows the track")
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith("build")]
        for fn in filenames:
            if os.path.splitext(fn)[1] not in TEXT_EXT and fn not in ("Makefile", "learn", "LICENSE", "NOTICE"):
                continue
            path = os.path.join(dirpath, fn)
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                continue
            if b"\0" in data[:1024]:
                continue
            for n, line in enumerate(data.splitlines(), 1):
                if any(b > 127 for b in line):
                    problems.append(f"{os.path.relpath(path, ROOT)}:{n}: non-ASCII character")
                    break
    for p in problems:
        print(p)
    for n in notes:
        print(n)
    print("check:", "ok" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


def cmd_serve(args):
    port = 8000
    if args:
        if args[0] != "--port" or len(args) != 2 or not args[1].isdigit():
            sys.exit("usage: learn serve [--port N]")
        port = int(args[1])
    from harness.web.server import serve
    return serve(port)


def cmd_export(args):
    if len(args) != 1 or args[0].startswith("-"):
        sys.exit("usage: learn export <outdir>")
    from harness.web.export import ExportError, export
    try:
        s = export(args[0])
    except ExportError as e:
        sys.exit(f"export: {e}")
    print(f"exported {s['pages']} pages to {args[0]}: {s['files']} files, {s['bytes'] / 1e6:.1f} MB; "
          f"Files views: {s['views']} lesson x file, stored as {s['stored']} distinct")
    for rel, path in s["leaks"]:
        print(f"{rel}: names a path on this machine: {path}")
    if s["leaks"]:
        print("export: fix these before you publish it")
        return 1
    return 0


def cmd_verify(args):
    from harness import verify
    return verify.main(args)


def cmd_selftest(args):
    import unittest
    suite = unittest.defaultTestLoader.discover(os.path.join(ROOT, "harness", "tests"),
                                                top_level_dir=ROOT)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def main(argv):
    cmd, args = (argv[0], argv[1:]) if argv else ("map", [])
    handlers = {"map": cmd_map, "test": cmd_test, "new": cmd_new,
                "new-track": cmd_new_track, "check": cmd_check,
                "serve": cmd_serve, "export": cmd_export, "selftest": cmd_selftest,
                "start": cmd_start, "status": cmd_status, "next": cmd_next, "extend": cmd_extend,
                "solution": cmd_solution, "check-skeleton": cmd_check_skeleton,
                "check-timeline": cmd_check_timeline, "verify": cmd_verify,
                "run": cmd_run, "bench": cmd_bench, "files": cmd_files}
    if cmd not in handlers:
        print(__doc__)
        return 2
    return handlers[cmd](args) or 0
