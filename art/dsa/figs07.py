"""Figures for dsa module 07, Building in order: make (lessons 07.01 to 07.04).

    python3 -B art/dsa/figs07.py

Nothing here is typed in by hand. The script writes the project as it stands at each lesson
(./learn files, in a temporary directory), builds it with the system's make, and draws every
figure from what that lesson's bin/make prints with DS_TRACE=1, so a figure cannot disagree with
the code. Two makefiles:

  MINI      a cut-down copy of the track's own build, with short names: two tools, freq and
            sort, each linked from its object and the library libds.a, which is archived from
            two objects; every object needs its source and the shared header ds.h. Each recipe
            touches its target, so it builds anywhere in a moment.
  loop.mk   tools/make/examples/diamond.mk, included, and two more rules that close a cycle:
            libb needs version.h, and version.h needs app (07.02's Run it types the same file).

  07.01-graph   still: MINI beside its graph, and how often 07.01's walk came to each node
                ("trace: walk DEPTH NAME") and ran its recipe ("trace: run NAME"): bin/make -n
  07.02-search  stepped: 07.02's depth-first search on loop.mk, one frame per trace line
                ("trace: enter 1 libb", "again", "leave", "cycle"), ending at the cycle
  07.03-order   stepped: 07.03's build in order on MINI, built once and then table.c touched:
                one frame per target checked ("trace: check table.o: table.c is newer")
  07.04-queue   stepped: 07.04's ready queue on MINI from nothing, bin/make -j 2: each frame
                one turn of the queue's loop ("trace: ready", "start", "skip", "finish")

The script checks what it draws against what it is drawn from: the graph against --graph, the
walk's count of each node against its paths, the order against every edge, the queue's counts.
"""
import atexit
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import figlib  # noqa: E402
from figlib import Fig, fmt, tw, write  # noqa: E402
import steps  # noqa: E402

figlib.LESSONS = os.path.join(ROOT, "tracks", "dsa", "lessons")
MOD = "07-make"

MINI = """# A cut-down copy of the track's build: two tools, a library of two objects.

all: freq sort

freq: freq.o libds.a
\ttouch freq
sort: sort.o libds.a
\ttouch sort
libds.a: util.o table.o
\ttouch libds.a
freq.o: freq.c ds.h
\ttouch freq.o
sort.o: sort.c ds.h
\ttouch sort.o
util.o: util.c ds.h
\ttouch util.o
table.o: table.c ds.h
\ttouch table.o

.PHONY: all
"""
SOURCES = ["freq.c", "util.c", "ds.h", "table.c", "sort.c"]
LOOP = "include tools/make/examples/diamond.mk\nlibb: version.h\nversion.h: app\n"

_top = []


def top():
    if not _top:
        d = tempfile.mkdtemp(prefix="dsa-figs07-")
        atexit.register(shutil.rmtree, d, True)
        _top.append(d)
    return _top[0]


_built = {}


def project(at):
    """The project at a lesson, written by ./learn files and built by the system's make."""
    if at not in _built:
        d = os.path.join(top(), at)
        subprocess.run([os.path.join(ROOT, "learn"), "files", "dsa", "--at", at, d], check=True,
                       stdout=subprocess.DEVNULL)
        subprocess.run(["make", "-s"], cwd=d, check=True, stdout=subprocess.DEVNULL)
        _built[at] = d
    return _built[at]


def mini(name):
    """A directory holding MINI as its Makefile and the five sources, nothing built."""
    d = os.path.join(top(), name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    with open(os.path.join(d, "Makefile"), "w") as f:
        f.write(MINI)
    for s in SOURCES:
        open(os.path.join(d, s), "w").close()
    return d


def make(at, args, cwd, trace=True):
    """(stdout, the trace lines without "trace: ") of the lesson's bin/make, run in cwd."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("DS_") and "MAKE" not in k}
    env["LC_ALL"] = "C"
    if trace:
        env["DS_TRACE"] = "1"
    r = subprocess.run([os.path.join(project(at), "bin", "make")] + args, cwd=cwd, env=env,
                       capture_output=True, text=True)
    lines = [l[len("trace: "):] for l in r.stderr.splitlines() if l.startswith("trace: ")]
    return r.returncode, r.stdout, lines, r.stderr


def graph_of(at, cwd, args=()):
    """(names in --graph's order, {name: [needs]}) as bin/make --graph prints them."""
    rc, out, _, err = make(at, ["--graph"] + list(args), cwd, trace=False)
    assert rc == 0, err
    names, needs = [], {}
    for line in out.splitlines():
        head, _, rest = line.partition(":")
        if head == ".PHONY":
            continue
        names.append(head)
        needs[head] = rest.split()
    return names, needs


# ------------------------------------------------------------------ drawing a graph

BH = 24                     # a node's box


def box_w(name):
    return tw(name, 11.5, True) + 18


class Layout:
    """Where each node of a graph is drawn: its centre."""

    def __init__(self, pos):
        self.pos = pos

    def edge(self, f, a, b, cls="m", width=None):
        """An arrow from a to b, the node a needs: from a's bottom edge to b's top edge."""
        (x1, y1), (x2, y2) = self.pos[a], self.pos[b]
        y1 += BH / 2
        y2 -= BH / 2 + 1.5
        if width:
            m = f' marker-end="url(#{f.key}-{f._marker(cls)})"'
            f.add(f'<line class="{cls}" x1="{fmt(round(x1, 1))}" y1="{fmt(round(y1, 1))}" x2="{fmt(round(x2, 1))}" '
                  f'y2="{fmt(round(y2, 1))}" stroke-width="{width}" stroke-linecap="round"{m}/>')
        else:
            f.line(round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1), cls, arrow=True)

    def node(self, f, name, state, label=None, badge=None):
        """state: new (muted, dashed), plain, open, done, hot (the step's own), ready, running."""
        x, y = self.pos[name]
        w = box_w(name)
        cls, tcls, weight, dash = {
            "new": ("m f", "tm", None, True),
            "plain": ("s f", "t", None, False),
            "open": ("a af", "ta", 700, False),
            "ready": ("a f", "ta", 700, False),
            "running": ("a af", "ta", 700, False),
            "done": ("a fa", "f", 700, False),
        }[state]
        if state == "running":
            f.add(f'<rect class="a" x="{fmt(round(x - w / 2 - 4, 1))}" y="{fmt(round(y - BH / 2 - 4, 1))}" '
                  f'width="{fmt(round(w + 8, 1))}" height="{BH + 8}" rx="9" stroke-width="1.5"/>')
        f.rect(round(x - w / 2, 1), y - BH / 2, round(w, 1), BH, cls, 6, dash=dash)
        f.text(x, y + 4, name, tcls, 11.5, "middle", weight, mono=True)
        if badge is not None:
            text, bcls = badge
            bw = tw(text, 10, True) + 8
            bx = x + w / 2 - 6
            f.add(f'<rect class="{bcls}" x="{fmt(round(bx, 1))}" y="{fmt(y - BH / 2 - 9)}" width="{fmt(round(bw, 1))}" '
                  f'height="15" rx="7.5" stroke-width="1.5"/>')
            f.text(round(bx + bw / 2, 1), y - BH / 2 + 2.5, text, "f" if "fa" in bcls else "ta", 10, "middle", 700,
                   mono=True)


def mini_layout(x0, x1, y0, dy):
    """MINI drawn top down: all; the tools; the library; the four objects; the five sources."""
    w = x1 - x0
    col = lambda k, n: x0 + w * (k + 0.5) / n          # noqa: E731
    pos = {"all": (col(0, 1), y0),
           "freq": (col(0, 2) + w * 0.06, y0 + dy), "sort": (col(1, 2) - w * 0.06, y0 + dy),
           "libds.a": (col(0, 1), y0 + 2 * dy)}
    for k, n in enumerate(["freq.o", "util.o", "table.o", "sort.o"]):
        pos[n] = (col(k, 4), y0 + 3 * dy)
    for k, n in enumerate(SOURCES):
        pos[n] = (col(k, 5), y0 + 4 * dy)
    return Layout(pos)


def legend(f, y, items, x=24):
    """One row: a small box in each state, and what it means."""
    for state, label in items:
        cls, dash = {"new": ("m f", True), "plain": ("s f", False), "open": ("a af", False),
                     "ready": ("a f", False), "running": ("a af", False), "done": ("a fa", False)}[state]
        if state == "running":
            f.rect(x - 3, y - 13, 24, 18, "a", 6)
        f.rect(x, y - 10, 18, 12, cls, 3, dash=dash)
        f.text(x + 26, y, label, "tm", 11)
        x += 26 + tw(label, 11) + 20
    return x


def arrow_key(f, x, y, label="needs"):
    f.line(x, y - 4, x + 26, y - 4, "m", arrow=True)
    f.text(x + 34, y, label, "tm", 11)


# ------------------------------------------------------------------ 07.01: the graph, and the walk

def graph0701():
    d = mini("walk")
    names, needs = graph_of("07.01", d)
    rc, out, tr, err = make("07.01", ["-n"], d)
    assert rc == 0, err
    visits, runs = {}, {}
    for line in tr:
        m = re.match(r"^walk \d+ (\S+)$", line)
        if m:
            visits[m.group(1)] = visits.get(m.group(1), 0) + 1
        m = re.match(r"^run (\S+)$", line)
        if m:
            runs[m.group(1)] = runs.get(m.group(1), 0) + 1

    # the walk comes to a node once for every path from all to it
    def paths(n, memo={}):
        if n not in memo:
            memo[n] = 1 if n == "all" else sum(paths(t) for t in names if n in needs[t])
        return memo[n]
    assert all(visits[n] == paths(n) for n in names), (visits, {n: paths(n) for n in names})
    assert sum(runs.values()) == len(out.splitlines())
    with_recipe = [n for n in names if n != "all" and n not in SOURCES]

    f = Fig("f0701a", "A cut-down copy of the track's build, beside the graph it becomes, and how often the walk "
            "comes to each node", 372)
    # the makefile, its rules (each recipe is touch and the target's name)
    f.text(24, 24, "Makefile (the rules)", "tm", 11)
    rules = [l for l in MINI.splitlines() if l and not l.startswith(("#", "\t"))]
    for i, l in enumerate(rules):
        f.text(24, 48 + i * 19, l, "t", 11, mono=True)
    yb = 48 + len(rules) * 19 + 6
    f.text(24, yb, "each recipe: touch, and", "tm", 10.5)
    f.text(24, yb + 15, "the target's own name", "tm", 10.5)
    # the graph
    lay = mini_layout(232, 624, 52, 62)
    f.text(428, 24, "the graph: each name one node", "tm", 11, "middle")
    for a in names:
        for b in needs[a]:
            hot = visits[a] > 1
            lay.edge(f, a, b, "a" if hot else "m")
    for n in names:
        k = visits[n]
        state = "plain" if k == 1 else "open"
        badge = (f"x{k}", "a fa") if k > 1 else None
        lay.node(f, n, state, badge=badge)
    # what the walk did
    total = sum(visits.values())
    ran = sum(runs.values())
    twice = [n for n in with_recipe if runs.get(n, 0) > 1]
    assert sorted(twice) == ["libds.a", "table.o", "util.o"] and max(runs.values()) == 2, runs
    y = 330
    f.text(24, y, f"bin/make -n, 07.01's walk: {total} visits to {len(names)} nodes, {ran} recipes run where "
           f"{len(with_recipe)} would do", "t", 11.5, weight=600)
    f.text(24, y + 20, f"xN: the walk came to that node N times, once for each path from all to it; in colour, "
           f"the edges it went down twice", "tm", 10.5)
    return f, (total, ran, len(with_recipe), visits)


# ------------------------------------------------------------------ 07.02: the search, and the cycle

def search0702():
    d = project("07.02")
    with open(os.path.join(d, "loop.mk"), "w") as fh:
        fh.write(LOOP)
    names, needs = graph_of("07.02", d, ["-f", "loop.mk"])
    rc, out, tr, err = make("07.02", ["-n", "-f", "loop.mk"], d)
    assert rc == 2 and out == "", (rc, out, err)
    msg = [l for l in err.splitlines() if l.startswith("make: ")]
    assert msg == ["make: dependency cycle: app -> libb -> version.h -> app"], msg
    events = [l.split() for l in tr]
    assert [e[0] for e in events][-1] == "cycle" and all(e[0] in ("enter", "leave", "again", "cycle") for e in events)

    f = Fig("f0702a", "Depth-first search on loop.mk: each node new, open or done, until the search meets an open "
            "node again", 330)
    f.text(24, 22, "loop.mk: diamond.mk, and two rules more", "tm", 11)
    f.text(24, 40, "libb: version.h", "t", 11, mono=True)
    f.text(160, 40, "version.h: app", "t", 11, mono=True)
    pos = {"app": (172, 82), "liba": (92, 150), "libb": (252, 150), "common.h": (152, 218), "version.h": (316, 218)}
    lay = Layout(pos)
    legend_y = 316
    x = legend(f, legend_y, [("new", "new"), ("open", "open: on the path"), ("done", "done")])
    arrow_key(f, x, legend_y)
    # the right-hand panel's frame
    PX = 418
    f.text(PX, 52, "the path, goal at the bottom", "tm", 11)
    f.text(PX, 202, "done, in the order finished", "tm", 11)

    def back_edge(cls, width=None):
        (x1, y1), (x2, y2) = pos["version.h"], pos["app"]
        d_ = (f"M{x1 + box_w('version.h') / 2:.1f} {y1} C {x1 + 80:.1f} {y1}, {x2 + 120:.1f} {y2}, "
              f"{x2 + box_w('app') / 2 + 2:.1f} {y2}")
        if width:
            m = f' marker-end="url(#{f.key}-{f._marker(cls)})"'
            f.add(f'<path class="{cls}" d="{d_}" stroke-width="{width}" stroke-linecap="round" fill="none"{m}/>')
        else:
            f.path(d_, cls, arrow=True)

    state = {n: "new" for n in names}
    path, done = [], []
    for k, e in enumerate(events):
        ev, depth, name = e[0], int(e[1]), e[2]
        hot_edge = None
        if ev == "enter":
            if path:
                hot_edge = (path[-1], name)
            assert depth == len(path)
            state[name] = "open"
            path.append(name)
            cap = (f"enter {name}: new, so the search opens it and puts it on the path, {depth} "
                   f"edge{'s' if depth != 1 else ''} below the goal." if depth else
                   "enter app, the goal: it is open, the first node on the path.")
            if name == "libb":
                cap = "enter libb: liba is done, so the search goes on along app's next edge, to libb, which is new."
        elif ev == "leave":
            assert path[-1] == name
            path.pop()
            state[name] = "done"
            done.append(name)
            cap = (f"leave {name}: everything it needs is done, so it is done too; it comes off the path "
                   f"and goes on the end of the finished list.")
            if not needs[name]:
                cap = f"leave {name}: it needs nothing, so it is done at once, the first node finished."
        elif ev == "again":
            hot_edge = (path[-1], name)
            cap = (f"again {name}: libb needs {name}, which is done already: a second way to it, not a "
                   f"cycle. The search does not go in again.")
        else:
            hot_edge = (path[-1], name)
            i = path.index(name)
            cyc = path[i:] + [name]
            cap = (f"cycle: version.h needs {name}, which is open: on the path. The path from {name} down to here "
                   f"is the cycle: make prints {' -> '.join(cyc)} and stops.")
        with steps.step(f, cap):
            for a in names:
                for b in needs[a]:
                    if a == "version.h" and b == "app":
                        continue
                    hot = hot_edge == (a, b)
                    on_path = a in path and b in path and path.index(b) == path.index(a) + 1
                    cls = "a" if hot or on_path else "m"
                    lay.edge(f, a, b, cls, width=2.5 if hot else None)
            hot = hot_edge == ("version.h", "app")
            back_edge("a" if hot else "m", 2.5 if hot else None)
            for n in names:
                lay.node(f, n, state[n])
            # the path, as a stack of frames
            for i, n in enumerate(path):
                y = 176 - i * 26
                w = 150
                f.rect(PX, y - 16, w, 22, "a af", 4)
                f.text(PX + 8, y - 1, str(i), "tm", 10, mono=True)
                f.text(PX + 24, y - 1, n, "ta", 11, weight=700, mono=True)
            if ev == "cycle":
                y = 176 - len(path) * 26
                f.rect(PX, y - 16, 150, 22, "a", 4, dash=True)
                f.text(PX + 8, y - 1, str(depth), "tm", 10, mono=True)
                f.text(PX + 24, y - 1, f"{name} again", "ta", 11, weight=700, mono=True)
            for i, n in enumerate(done):
                f.text(PX + 8 + i * 84, 222, f"{i + 1}. {n}", "t", 11, weight=600, mono=True)
            if not done:
                f.text(PX + 8, 222, "(none yet)", "tm", 11)
            line = f"trace: {' '.join(e)}"
            f.text(PX, 262, line, "ta", 11, weight=600, mono=True)
            if ev == "cycle":
                f.text(PX, 284, "make: dependency cycle:", "t", 10.5, mono=True)
                f.text(PX, 300, "app -> libb -> version.h -> app", "t", 10.5, mono=True)
    return f, len(events)


# ------------------------------------------------------------------ 07.03: in order, and out of date

def order0703():
    d = mini("order")
    names, needs = graph_of("07.03", d)
    rc, out, tr, err = make("07.03", ["--order"], d, trace=False)
    order = out.split()
    pos_in = {n: i for i, n in enumerate(order)}
    assert sorted(order) == sorted(names)
    assert all(pos_in[b] < pos_in[a] for a in names for b in needs[a]), "not a topological order"
    rc, out, _, err = make("07.03", [], d, trace=False)          # build it all once
    assert rc == 0, err
    time.sleep(0.05)
    os.utime(os.path.join(d, "table.c"))                        # then change one source: touch table.c
    rc, out, tr, err = make("07.03", [], d)
    assert rc == 0, err
    checks = []
    for line in tr:
        m = re.match(r"^check (\S+): (.*)$", line)
        if m:
            checks.append((m.group(1), m.group(2)))
    assert [c[0] for c in checks] == order
    ran = out.split("\n")
    made = [n for n, why in checks if why not in ("up to date", "a file with no rule")]
    assert [l for l in ran if l] == [f"touch {n}" for n in made if n != "all"], (ran, made)

    f = Fig("f0703a", "The build in order on the cut-down build, after touch table.c: each target checked once, "
            "after everything it needs", 404)
    f.text(24, 22, "touch table.c, then bin/make: the targets in the search's finishing order", "tm", 11)
    lay = mini_layout(16, 420, 58, 62)
    OX = 444
    f.text(OX, 44, "--order", "tm", 11, mono=True)
    y_leg = 392
    x = legend(f, y_leg, [("new", "not checked yet"), ("plain", "up to date"), ("done", "out of date: made")])
    arrow_key(f, x, y_leg)

    # frames: the touch, then each target with a rule, the sources it needed checked with it
    frames, pending = [("touch", None, [])], []
    for n, why in checks:
        pending.append((n, why))
        if why != "a file with no rule":
            frames.append(("check", n, pending))
            pending = []
    assert not pending
    seen, made_so_far = set(), []
    for kind, n, group in frames:
        for g, why in group:
            seen.add(g)
            if why not in ("up to date", "a file with no rule"):
                made_so_far.append(g)
        why = group[-1][1] if group else None
        if kind == "touch":
            cap = ("Everything was built once; then table.c is touched, and is now newer than table.o. "
                   "Nothing is checked yet.")
        else:
            leaves = [g for g, w in group[:-1]]
            pre = ""
            if leaves:
                pre = (f"{leaves[0]} is a file with no rule, and there. " if len(leaves) == 1 else
                       f"{' and '.join(leaves)} are files with no rule, and there. ")
            if why == "up to date":
                cap = f"{pre}{n} is up to date: nothing it needs was made, and none of it is newer."
            elif why == "phony":
                ran = [g for g in made_so_far if g != "all"]
                cap = (f"all is phony, so it is always out of date, and it has no recipe to run. The build ran "
                       f"{len(ran)} recipes: {', '.join(ran[:-1])} and {ran[-1]}.")
            else:
                cap = f"{pre}{n}: {why}, so {n} is out of date: its recipe runs, touch {n}."
        with steps.step(f, cap):
            for a in names:
                for b in needs[a]:
                    hot = n == a
                    lay.edge(f, a, b, "a" if hot and b in made_so_far else ("s" if hot else "m"))
            for m_ in names:
                if m_ not in seen:
                    st = "new"
                elif m_ in made_so_far:
                    st = "done"
                else:
                    st = "plain"
                lay.node(f, m_, st)
            if n is not None:
                x0, y0 = lay.pos[n]
                w = box_w(n)
                f.add(f'<rect class="a" x="{fmt(round(x0 - w / 2 - 4, 1))}" y="{fmt(y0 - BH / 2 - 4)}" '
                      f'width="{fmt(round(w + 8, 1))}" height="{BH + 8}" rx="9" stroke-width="2"/>')
            # the order, with what has been checked
            for i, o in enumerate(order):
                y = 64 + i * 22
                if o in made_so_far:
                    cls, tcls, wt = "a fa", "f", 700
                elif o in seen:
                    cls, tcls, wt = "s f", "t", None
                else:
                    cls, tcls, wt = "m f", "tm", None
                f.rect(OX, y - 14, 92, 19, cls, 4, dash=o not in seen)
                f.text(OX + 8, y, o, tcls, 10.5, weight=wt, mono=True)
                if o == n:
                    f.text(OX + 100, y, "<- now", "ta", 10.5, weight=700)
            f.text(24, 362, "out of date: " + (", ".join(made_so_far) if made_so_far else "(nothing yet)"),
                   "ta" if made_so_far else "tm", 11.5, weight=600, mono=bool(made_so_far))
    return f, (order, checks, made)


# ------------------------------------------------------------------ 07.04: a queue of ready work

def queue0704():
    d = mini("queue")
    names, needs = graph_of("07.04", d)
    rc, out, tr, err = make("07.04", ["-j", "2"], d)
    assert rc == 0, err
    events = []
    for line in tr:
        m = re.match(r"^(ready|start|skip|finish) (\S+)$", line)
        if m:
            events.append((m.group(1), m.group(2)))
    needed_by = {n: [t for t in names if n in needs[t]] for n in names}
    # frames: one turn of the queue's loop each (what wait() said, then what started), with the first
    # turn's start split into the sources being queued, and the sources coming off the queue
    cuts = [0]
    for i, (ev, n) in enumerate(events):
        if i and ev == "skip" and events[i - 1][0] == "ready" and len(cuts) == 1:
            cuts.append(i)
        if ev == "start" and cuts[-1] < i and not any(e[0] == "start" for e in events[cuts[-1]:i]) and \
                all(e[0] in ("ready", "skip", "finish") for e in events[cuts[-1]:i]) and len(cuts) == 2:
            cuts.append(i)
        if ev == "finish" and any(e == ("start", n) for e in events[:i]) and events[i - 1] != ("start", n) \
                and any(e[0] == "start" for e in events[cuts[-1]:i]):
            cuts.append(i)
    cuts.append(len(events))
    groups = [events[a:b] for a, b in zip(cuts, cuts[1:]) if b > a]

    f = Fig("f0704a", "bin/make -j 2 on the cut-down build: each target waits for its count of unfinished prerequisites "
            "to fall to 0, then joins the queue", 404)
    f.text(24, 22, "bin/make -j 2, nothing built yet: the number on each target is how many of its needs are "
           "not finished", "tm", 11)
    lay = mini_layout(16, 420, 62, 62)
    QX = 444
    f.text(QX, 50, "ready queue, front first", "tm", 11)
    f.text(QX, 214, "running (-j 2: two at most)", "tm", 11)
    y_leg = 392
    x = legend(f, y_leg, [("plain", "waiting"), ("ready", "ready, queued"), ("running", "running"),
                          ("done", "finished")])
    arrow_key(f, x, y_leg)

    waiting = {n: len(needs[n]) for n in names}
    state = {n: "plain" for n in names}
    queue, running, finished = [], [], []
    most = 0
    for k, g in enumerate(groups):
        fin, rdy, st, sk, said = [], [], [], [], []
        prev = None
        for ev, n in g:
            if ev == "ready":
                assert waiting[n] == 0, (n, waiting[n])
                queue.append(n)
                state[n] = "ready"
                rdy.append(n)
            elif ev in ("start", "skip"):
                assert queue and queue[0] == n, (queue, n)
                queue.pop(0)
                if ev == "start":
                    running.append(n)
                    state[n] = "running"
                    st.append(n)
                else:
                    sk.append(n)
            else:
                if n in running:
                    running.remove(n)
                state[n] = "done"
                finished.append(n)
                fin.append(n)
                for t in needed_by[n]:
                    waiting[t] -= 1
                if prev != ("start", n):          # a recipe that ran, not one with nothing to run
                    said.append(f"{n} finishes" + (": " + ", ".join(
                        f"{t} {'now waits for ' + str(waiting[t]) if waiting[t] else 'reaches 0'}"
                        for t in needed_by[n]) if needed_by[n] else ""))
            most = max(most, len(running))
            prev = (ev, n)
        assert len(running) <= 2
        if k == 0:
            cap = (f"Each target waits for as many targets as it needs. The {len(rdy)} sources need none: "
                   f"they are ready, and queued in the search's order.")
        elif sk and not st:
            fresh = [n for n in rdy]
            cap = (f"The sources come off the queue up to date (files with no rule), so each is finished at "
                   f"once. Every object's count falls to 0: {', '.join(fresh)} join the queue.")
        elif sk or (st and not fin):
            cap = (f"Two may run at once: {' and '.join(st)} come off the front of the queue and start.")
        else:
            cap = "; ".join(said) + "."
            joined = [n for n in rdy if n != "all"]
            if joined:
                cap += f" {' and '.join(joined)} {'joins' if len(joined) == 1 else 'join'} the queue."
            started = [n for n in st if n != "all"]
            if started:
                cap += (f" {' and '.join(started)} {'starts' if len(started) == 1 else 'start'} in the free "
                        f"slot{'s' if len(started) > 1 else ''}.")
            if not started and not joined and running:
                cap += f" Nothing is ready, so {running[0]} runs alone."
            if "all" in finished:
                cap += (" all joins the queue; it is phony, with no recipe, so it is finished as soon as it "
                        "comes off, and the build is done.")
        with steps.step(f, cap):
            for a in names:
                for b in needs[a]:
                    lay.edge(f, a, b, "a" if state[b] == "done" else "m")
            for n in names:
                badge = None
                if state[n] in ("plain",) or (state[n] != "done" and needs[n]):
                    badge = (str(waiting[n]), "a fa" if waiting[n] == 0 else "s f")
                lay.node(f, n, state[n], badge=badge if state[n] != "done" else None)
            for i, n in enumerate(queue):
                x0 = QX + (i % 3) * 62
                y0 = 60 + (i // 3) * 28
                w = 58
                f.rect(x0, y0, w, 22, "a f", 4)
                f.text(x0 + w / 2, y0 + 15, n, "ta", 10.5, "middle", 700, mono=True)
            if not queue:
                f.text(QX, 76, "(empty)", "tm", 11)
            for i in range(2):
                y0 = 224 + i * 30
                if i < len(running):
                    f.rect(QX, y0, 120, 24, "a af", 4)
                    f.text(QX + 10, y0 + 16, f"touch {running[i]}", "ta", 10.5, weight=700, mono=True)
                else:
                    f.rect(QX, y0, 120, 24, "m", 4, dash=True)
                    f.text(QX + 10, y0 + 16, "(free)", "tm", 10.5)
            f.text(QX, 310, f"finished: {len(finished)} of {len(names)}", "t", 11, weight=600)
    assert waiting["all"] == 0 and len(finished) == len(names) and most == 2
    return f, len(groups)


# ------------------------------------------------------------------ main

def save(name, f, stepped=False):
    p = write(MOD, name, f)
    text = open(p).read()
    n = steps.check(text) if stepped else 0
    sys.path.insert(0, ROOT)
    from harness.web.art import sanitize
    clean = sanitize(text, "x")
    if not clean:
        raise SystemExit(f"{p}: rejected by the sanitizer")
    if clean.count("<") - clean.count("</") != text.count("<") - text.count("</"):
        raise SystemExit(f"{p}: the sanitizer dropped an element")
    if len(text) > 200 * 1024:
        raise SystemExit(f"{p}: {len(text)} bytes, over the 200 KB a figure may be")
    print(f"{os.path.relpath(p, ROOT)}: {len(text)} bytes" + (f", {n} steps" if stepped else ""))


def main():
    f, info = graph0701()
    save("07.01-graph", f)
    print("  walk:", info[:3])
    f, n = search0702()
    save("07.02-search", f, stepped=True)
    f, info = order0703()
    save("07.03-order", f, stepped=True)
    print("  order:", " ".join(info[0]), "| made:", info[2])
    f, n = queue0704()
    save("07.04-queue", f, stepped=True)


if __name__ == "__main__":
    main()
