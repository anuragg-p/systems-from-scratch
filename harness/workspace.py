"""Learner workspaces: build every lesson yourself.

A track's reference code marks what each lesson builds:

    // @build 02.02 kalloc
    // Pop one page off kmem.freelist while holding kmem.lock. Fill it
    // with 5s so callers cannot rely on zeroes. Return 0 if none is free.
    ...the reference code...
    // @end

The comment lines right after @build are the instructions: the concept
and the contract. An optional "@stub <code>" line among them overrides
the track's default stub for that one region.

`./learn start <track>` copies the track into work/<track>/ and cuts the
current lesson's regions: the reference code between the instructions and
@end is replaced by a stub that fails loudly ("02.02: kalloc not written
yet"). So the system always builds and runs, with exactly one hole - the
one you are filling. Lessons behind you hold your code; lessons ahead
still hold the reference, so the rest of the system keeps working.

Optional modules (extensions, `optional: true` in a module's README.md)
are opt-in and independent. `advance` walks the core lessons in order and
stops after the last one; `extend` starts one extension once the core is
built, and `advance` then walks that extension alone and stops at its end.

Nothing here knows what language a track is written in. Comment leaders
(// # ; --) and stubs come from the track.
"""

import fnmatch
import json
import os
import re
import shutil

from harness.core import ROOT, Fail, lesson_key, module_id

# LEARN_WORK_DIR relocates the learner workspaces (the web tests use it).
WORK_DIR = os.environ.get("LEARN_WORK_DIR") or os.path.join(ROOT, "work")
STATE_FILE = ".learn.json"
NOT_COPIED = {"lessons", "tests", "track.py", "__pycache__", ".test-logs"}
# Files at the top of a track that are about the track (its picture on the site), not part of the system.
TRACK_FILES = {"art.svg", "icon.svg"}

LEADER = r"(//|#|;|--)"
BUILD_RE = re.compile(r"^(\s*)" + LEADER + r"\s*@build\s+(\d\d\.\d\d)\s*(.*?)\s*$")
END_RE = re.compile(r"^\s*" + LEADER + r"\s*@end\b")
STUB_RE = re.compile(r"^\s*" + LEADER + r"\s*@stub\s?(.*)$")
# The timeline's blocks (harness/timeline.py): "@from NN.LL" and "@internal" open one, "@end"
# closes it. They may sit inside a @build region; its own @end is the first one outside them.
BLOCK_RE = re.compile(r"^\s*(//|#|;|--|/\*)\s*@(from\s+\d\d\.\d\d|internal)\s*(\*/)?\s*$")


class Region:
    """One @build ... @end block in one file."""

    def __init__(self, path, lesson, title, indent, leader, start, instr_end, end, stub):
        self.path = path            # relative to the tree root
        self.lesson = lesson
        self.title = title
        self.indent = indent
        self.leader = leader
        self.start = start          # index of the @build line
        self.instr_end = instr_end  # index of the first code line
        self.end = end              # index of the @end line
        self.stub = stub            # override, or None

    @property
    def line(self):
        return self.start + 1


def _is_comment(line, leader):
    return line.strip().startswith(leader)


def scan_text(path, text):
    lines = text.split("\n")
    regions = []
    i = 0
    while i < len(lines):
        m = BUILD_RE.match(lines[i])
        if not m:
            i += 1
            continue
        indent, leader, lesson, title = m.group(1), m.group(2), m.group(3), m.group(4)
        j = i + 1
        stub = None
        while (j < len(lines) and _is_comment(lines[j], leader) and not END_RE.match(lines[j])
               and not BLOCK_RE.match(lines[j])):
            sm = STUB_RE.match(lines[j])
            if sm:
                stub = sm.group(2)
            j += 1
        k, depth = j, 0
        while k < len(lines):
            if BUILD_RE.match(lines[k]):
                raise Fail(f"{path}:{k + 1}: @build inside another @build (from line {i + 1})")
            if BLOCK_RE.match(lines[k]):
                depth += 1
            elif END_RE.match(lines[k]):
                if depth == 0:
                    break
                depth -= 1
            k += 1
        if k == len(lines):
            raise Fail(f"{path}:{i + 1}: @build {lesson} has no @end")
        regions.append(Region(path, lesson, title, indent, leader, i, j, k, stub))
        i = k + 1
    return regions


def source_files(track_module, root):
    """Files of a tree that may hold @build regions."""
    patterns = getattr(track_module, "SOURCES", ["*"])
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in NOT_COPIED and not d.startswith("build")]
        for fn in filenames:
            rel = os.path.relpath(os.path.join(dirpath, fn), root)
            if any(fnmatch.fnmatch(rel, p) for p in patterns):
                out.append(rel)
    return sorted(out)


def scan_tree(track_module, root):
    regions = []
    for rel in source_files(track_module, root):
        with open(os.path.join(root, rel), errors="replace") as f:
            regions += scan_text(rel, f.read())
    return regions


def lessons_with_regions(track_module, root):
    return sorted({r.lesson for r in scan_tree(track_module, root)}, key=lesson_key)


def stub_text(track_module, region):
    if region.stub is not None:
        return region.stub
    stubs = getattr(track_module, "STUBS", {})
    ext = os.path.splitext(region.path)[1]
    tmpl = stubs.get(ext, stubs.get("*", "TODO {id}"))
    return tmpl.format(id=region.lesson, title=region.title)


def cut(track_module, root, lesson):
    """Replace the code of every region of `lesson` under root with stubs."""
    changed = []
    for rel in source_files(track_module, root):
        path = os.path.join(root, rel)
        with open(path, errors="replace") as f:
            text = f.read()
        regions = [r for r in scan_text(rel, text) if r.lesson == lesson]
        if not regions:
            continue
        lines = text.split("\n")
        for r in reversed(regions):
            lines[r.instr_end:r.end] = [r.indent + stub_text(track_module, r)]
        with open(path, "w") as f:
            f.write("\n".join(lines))
        changed += [(rel, r) for r in regions]
    return changed


def region_code(root, region):
    with open(os.path.join(root, region.path), errors="replace") as f:
        lines = f.read().split("\n")
    return lines[region.instr_end:region.end], lines[region.start:region.instr_end]


# ---------------------------------------------------------------- state

def work_root(track):
    return os.path.join(WORK_DIR, track.id)


def load_state(track):
    path = os.path.join(work_root(track), STATE_FILE)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def save_state(track, state):
    with open(os.path.join(work_root(track), STATE_FILE), "w") as f:
        json.dump(state, f, indent=2)


def copy_track(track, dest):
    def ignore(dirpath, names):
        top = os.path.abspath(dirpath) == os.path.abspath(track.root)
        return [n for n in names
                if n in NOT_COPIED or n.startswith("build") or (top and (n == "work" or n in TRACK_FILES))]
    shutil.copytree(track.root, dest, ignore=ignore)


# ---------------------------------------------------------------- core and extensions

def group(track, lid):
    """None for a core lesson; the module id for a lesson of an optional extension."""
    return module_id(lid) if track.is_optional(lid) else None


def core_order(track, order=None):
    order = lessons_with_regions(track.module, track.root) if order is None else order
    return [l for l in order if not track.is_optional(l)]


def extension_order(track, mid, order=None):
    order = lessons_with_regions(track.module, track.root) if order is None else order
    return [l for l in order if module_id(l) == mid]


def behind(track, lid, order):
    """The lessons with regions that come before `lid` on its own path: earlier core lessons for a
    core lesson; every core lesson and the earlier ones of its module for an extension's lesson."""
    k = lesson_key(lid)
    if track.is_optional(lid):
        mid = module_id(lid)
        return [l for l in order if not track.is_optional(l) or (module_id(l) == mid and lesson_key(l) < k)]
    return [l for l in order if not track.is_optional(l) and lesson_key(l) < k]


def position(track, state, lid, order=None):
    """Where lesson `lid` stands for the learner: None (no workspace), "current", "behind" (built,
    or passed on the way) or "ahead" (not reached; for an extension: not started yet)."""
    if state is None:
        return None
    cur = state.get("current")
    if lid == cur:
        return "current"
    if lid in state.get("done", []):
        return "behind"
    if track.is_optional(lid):
        mid = module_id(lid)
        if cur and module_id(cur) == mid and lesson_key(lid) < lesson_key(cur):
            return "behind"
        mine = extension_order(track, mid, order)
        done = set(state.get("done", []))
        return "behind" if mine and all(l in done for l in mine) else "ahead"
    if cur is None or track.is_optional(cur):
        return "behind"          # the core is behind you
    return "behind" if lesson_key(lid) < lesson_key(cur) else "ahead"


def progress(track, state, order=None):
    """Counts and stage for a workspace state (None: no workspace).

    stage is one of: none (no workspace), core (a core lesson is current), extension (an
    extension's lesson is current), core-complete (every core lesson built, no extension
    finished), extension-complete (no lesson current and an extension finished, so the last
    thing done was an extension), idle (no lesson current, but core lessons are left: the
    track gained lessons after the learner finished, or the state was edited by hand)."""
    order = lessons_with_regions(track.module, track.root) if order is None else order
    done = set((state or {}).get("done", []))
    cur = (state or {}).get("current")
    core = core_order(track, order)
    core_left = [l for l in core if l not in done]
    exts = []
    for m in track.optional_modules:
        mine = extension_order(track, m.id, order)
        n = sum(1 for l in mine if l in done)
        here = bool(cur) and module_id(cur) == m.id
        exts.append({"id": m.id, "title": m.title, "done": n, "total": len(mine),
                     "complete": bool(mine) and n == len(mine), "current": here, "started": here or n > 0})
    if state is None:
        stage = "none"
    elif cur:
        stage = "extension" if track.is_optional(cur) else "core"
    elif core_left:
        stage = "idle"
    else:
        stage = "extension-complete" if any(e["complete"] for e in exts) else "core-complete"
    return {"stage": stage, "core": {"done": len(core) - len(core_left), "total": len(core),
                                     "complete": not core_left, "left": core_left},
            "extension": module_id(cur) if cur and track.is_optional(cur) else None, "extensions": exts}


def start(track, at=None, force=False):
    dest = work_root(track)
    if os.path.exists(dest):
        if not force:
            raise Fail(f"{os.path.relpath(dest, ROOT)} already exists; ./learn status {track.id}, "
                       f"or start over with --force")
        shutil.rmtree(dest)
    order = lessons_with_regions(track.module, track.root)
    if not order:
        raise Fail(f"track {track.id} has no @build regions yet")
    core = core_order(track, order)
    if at is None and not core:
        raise Fail(f"track {track.id} has no core lessons to build, only extensions: start one with --at NN.LL")
    current = at or core[0]
    if current not in order:
        raise Fail(f"lesson {current} builds nothing; lessons that do: {' '.join(order)}")
    copy_track(track, dest)
    changed = cut(track.module, dest, current)
    # A fresh copy holds the reference everywhere, so starting inside an extension means
    # starting on a finished core.
    save_state(track, {"current": current, "done": behind(track, current, order)})
    return current, changed


def unwritten(track_module, root, lesson):
    """Regions of `lesson` under root that still hold nothing but their stub."""
    out = []
    for r in scan_tree(track_module, root):
        if r.lesson != lesson:
            continue
        code, _ = region_code(root, r)
        body = [l.strip() for l in code if l.strip()]
        if body == [stub_text(track_module, r).strip()]:
            out.append(r)
    return out


def fill(track_module, root, ref_root, lesson):
    """Put the reference code back into every region of `lesson` under root."""
    ref = {}
    for r in scan_tree(track_module, ref_root):
        if r.lesson == lesson:
            ref[(r.path, r.title)] = region_code(ref_root, r)[0]
    for rel in source_files(track_module, root):
        path = os.path.join(root, rel)
        with open(path, errors="replace") as f:
            text = f.read()
        regions = [r for r in scan_text(rel, text) if r.lesson == lesson]
        if not regions:
            continue
        lines = text.split("\n")
        for r in reversed(regions):
            if (rel, r.title) in ref:
                lines[r.instr_end:r.end] = ref[(rel, r.title)]
        with open(path, "w") as f:
            f.write("\n".join(lines))


def advance(track, use_solution=False):
    """Finish the current lesson and cut out the next one.

    Refuses while the current lesson still holds its stub, because every
    later lesson runs on top of it. use_solution fills the current lesson
    with the reference code instead - an honest way to skip it.

    The next lesson is the next one on the same path: a core lesson leads
    only to core lessons, an extension's lesson only to that extension's.
    After the last one there is no current lesson (core complete, or
    extension complete); an extension is then started with extend().
    """
    state = load_state(track)
    if state is None:
        raise Fail(f"no workspace yet: ./learn start {track.id}")
    order = lessons_with_regions(track.module, track.root)
    cur = state.get("current")
    if not cur:
        raise Fail(f"no lesson in progress in {track.id}; ./learn status {track.id} shows what is left")
    if use_solution:
        fill(track.module, work_root(track), track.root, cur)
    else:
        left = unwritten(track.module, work_root(track), cur)
        if left:
            where = ", ".join(f"{r.path}:{r.line}" for r in left)
            raise Fail(f"{cur} is not written yet ({where}). Every later lesson runs on top of it. "
                       f"Write it, or move on with the reference code: ./learn next {track.id} --use-solution")
    path = group(track, cur)
    later = [l for l in order if lesson_key(l) > lesson_key(cur) and group(track, l) == path]
    state["done"] = sorted(set(state.get("done", [])) | {cur}, key=lesson_key)
    if not later:
        state["current"] = None
        save_state(track, state)
        return None, []
    nxt = later[0]
    changed = cut(track.module, work_root(track), nxt)
    state["current"] = nxt
    save_state(track, state)
    return nxt, changed


def missing_files(track, root):
    """Files of the track that a workspace copy would hold but `root` lacks: added to the track
    after the workspace was made (an extension written later, say)."""
    out = []
    for dirpath, dirnames, filenames in os.walk(track.root):
        top = os.path.abspath(dirpath) == os.path.abspath(track.root)
        dirnames[:] = sorted(d for d in dirnames
                             if d not in NOT_COPIED and not d.startswith("build") and not (top and d == "work"))
        for fn in sorted(filenames):
            if fn in NOT_COPIED or fn.startswith("build") or (top and fn in TRACK_FILES):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), track.root)
            if not os.path.lexists(os.path.join(root, rel)):
                out.append(rel)
    return out


def extend(track, mid, fill_core=False):
    """Start the optional extension `mid`: cut out its first unbuilt lesson and make it current.

    Allowed when no lesson is current and the core is built. While core lessons are left it
    refuses, naming them, unless fill_core: then every unbuilt core lesson (the current one
    too) gets the reference code first and counts as built, so the extension runs on a
    complete system. Never while another extension is in progress, and never over an
    extension already built (cutting it would throw the learner's code away).

    Files the track gained after the workspace was made are copied in first; if the
    extension's regions sit in files the workspace already has without them, it refuses
    rather than start a lesson with no hole to fill."""
    mod = track.modules.get(mid)
    if mod is None:
        raise Fail(f"track {track.id} has no module {mid}")
    if not mod.optional:
        raise Fail(f"module {mid} {mod.title} is part of the core, not an extension")
    state = load_state(track)
    if state is None:
        raise Fail(f"no workspace yet: ./learn start {track.id}")
    order = lessons_with_regions(track.module, track.root)
    mine = extension_order(track, mid, order)
    if not mine:
        raise Fail(f"extension {mid} {mod.title} builds nothing yet")
    done = set(state.get("done", []))
    todo = [l for l in mine if l not in done]
    if not todo:
        raise Fail(f"extension {mid} {mod.title} is already built")
    cur = state.get("current")
    if cur and track.is_optional(cur):
        if module_id(cur) == mid:
            raise Fail(f"you are already building extension {mid} {mod.title}: your lesson is {cur}")
        other = track.modules[module_id(cur)]
        raise Fail(f"you are in the middle of extension {other.id} {other.title} (lesson {cur}). "
                   f"Extensions run one at a time: finish it first with ./learn next {track.id}")
    core_left = [l for l in core_order(track, order) if l not in done]
    if core_left and not fill_core:
        n = len(core_left)
        raise Fail(f"the core is not finished: {n} core lesson{'' if n == 1 else 's'} "
                   f"{'is' if n == 1 else 'are'} not built yet ({' '.join(core_left)}). "
                   f"Extensions run on a finished system. Finish the core first, or fill every unbuilt "
                   f"core lesson with the reference code and start now: ./learn extend {track.id} {mid} --fill-core")
    root = work_root(track)
    missing = set(missing_files(track, root))
    stale = []
    for r in scan_tree(track.module, track.root):
        if module_id(r.lesson) != mid or r.path in missing:
            continue
        try:
            with open(os.path.join(root, r.path), errors="replace") as f:
                have = {(w.lesson, w.title) for w in scan_text(r.path, f.read())}
        except (OSError, Fail):
            have = set()
        if (r.lesson, r.title) not in have and r.path not in stale:
            stale.append(r.path)
    if stale:
        raise Fail(f"your workspace was made before extension {mid} {mod.title} was written: "
                   f"{', '.join(stale)} in {os.path.relpath(root, ROOT)} lack its @build regions, "
                   f"so there would be nothing to fill in. Nothing was changed.")
    if fill_core:
        for l in core_left:
            fill(track.module, root, track.root, l)
        done |= set(core_left)
    for rel in sorted(missing):
        os.makedirs(os.path.dirname(os.path.join(root, rel)) or root, exist_ok=True)
        shutil.copy2(os.path.join(track.root, rel), os.path.join(root, rel))
    first = todo[0]
    changed = cut(track.module, root, first)
    state["done"] = sorted(done, key=lesson_key)
    state["current"] = first
    save_state(track, state)
    return first, changed
