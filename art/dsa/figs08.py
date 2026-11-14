"""Figures for dsa module 08, Finding the way: route (lessons 08.01-08.04).

    python3 -B art/dsa/figs08.py

Nothing here is typed in by hand. The script writes the project as it stands at 08.04 into
build/figs08/ (./learn files), builds it, and draws every figure from what that build's
bin/route prints:

  tiny.map      the made-up map of a dozen junctions (ours: no credit needed). The stepped
                figures are its DS_TRACE=1 lines for the route from 3 to 8, one frame per
                junction finished: bfs (08.02), dijkstra (08.03) and astar (08.04). The
                adjacency lists of 08.01 are build_lists's two passes, done again here on the
                same file in the same order.
  london.map    central London from OpenStreetMap (ODbL). Every picture of it carries the
                credit line the tool itself draws, from the map's own "credit" line. Routes
                are bin/route's output; the junctions a search finished are its DS_TRACE
                "finish" lines. The pairs are the ones the lessons run.

A picture of London has thousands of roads, and a lesson figure may be 200 KB, so the roads
are thinned to fit: drawn on a grid of whole units of some metres (about a pixel of the
figure), a road whose two ends fall on the same point left out, the rest joined into
chains, one path per layer. Each layer is a <g> with a transform, styled only by the .art
classes, so the pictures work in the dark theme too.
"""
import math
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import figlib  # noqa: E402
from figlib import Fig, fmt, tw  # noqa: E402
import steps  # noqa: E402

figlib.LESSONS = os.path.join(ROOT, "tracks", "dsa", "lessons")
MOD = "08-route"
PROJECT = os.path.join(ROOT, "build", "figs08")


# ------------------------------------------------------------------ the real program

def build():
    shutil.rmtree(PROJECT, ignore_errors=True)            # ./learn files wants a new directory
    subprocess.run([os.path.join(ROOT, "learn"), "files", "dsa", "--at", "08.04", PROJECT], cwd=ROOT,
                   check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["make", "-s"], cwd=PROJECT, check=True)


def route(*args, trace=False):
    """bin/route's stdout and stderr, with DS_TRACE=1 when trace."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("DS_")}
    env["LC_ALL"] = "C"
    if trace:
        env["DS_TRACE"] = "1"
    r = subprocess.run([os.path.join(PROJECT, "bin", "route")] + list(args), cwd=PROJECT, env=env,
                       capture_output=True, text=True)
    if r.returncode not in (0, 1):
        raise SystemExit(f"route {' '.join(args)}: exit {r.returncode}: {r.stderr}")
    return r.stdout, r.stderr


def load_map(name):
    """(xy, roads, credit) of tools/route/NAME: xy[j] = (x, y), roads = [(a, b, metres)]."""
    xy, roads, credit, mode = [], [], None, None
    with open(os.path.join(PROJECT, "tools", "route", name)) as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            if line.startswith("credit "):
                credit = line[7:]
            elif line.startswith("junctions "):
                mode = "j"
            elif line.startswith("roads "):
                mode = "r"
            elif mode == "j":
                x, y = line.split()
                xy.append((int(x), int(y)))
            else:
                a, b, m = line.split()
                roads.append((int(a), int(b), int(m)))
    return xy, roads, credit


def path_of(out):
    """The junctions of a route bin/route printed, from FROM to TO, and its summary line."""
    lines = out.splitlines()
    return [int(l.split()[1]) for l in lines[2:]], lines[0]


def parse_trace(err, algo):
    """One dict per line of DS_TRACE: kind (finish or skip), j, d, frm, guess, sum, and items,
    the container after it: [(junction, value, old)]."""
    pat = re.compile(r"^trace: (\S+): (finish|skip) (\d+) at (\d+)(?:, guess (\d+), sum (\d+))?"
                     r"(?: \((?:from (\d+)|start)\))?(?:, finished at \d+ already)?; (\w+):(.*)$")
    out = []
    for line in err.splitlines():
        m = pat.match(line)
        if not m or m.group(1) != algo:
            continue
        items = []
        for tok in m.group(9).split():
            t = re.match(r"^(\d+):(\d+)(\(old\))?$", tok)
            items.append((int(t.group(1)), int(t.group(2)), bool(t.group(3))))
        out.append({"kind": m.group(2), "j": int(m.group(3)), "d": int(m.group(4)),
                    "guess": int(m.group(5)) if m.group(5) else None, "sum": int(m.group(6)) if m.group(6) else None,
                    "frm": int(m.group(7)) if m.group(7) else None, "box": m.group(8), "items": items})
    return out


# ------------------------------------------------------------------ tiny.map, drawn

def tx(x):
    return 52 + (x - 100) * 0.41


def ty(y):
    return 46 + (600 - y) * 0.34


R = 12          # a junction's circle


def road_key(a, b):
    return (min(a, b), max(a, b))


def draw_roads(f, xy, roads, labels=True, cls="m"):
    for a, b, m in roads:
        f.line(tx(xy[a][0]), ty(xy[a][1]), tx(xy[b][0]), ty(xy[b][1]), cls)
    if not labels:
        return
    for a, b, m in roads:
        (x1, y1), (x2, y2) = (tx(xy[a][0]), ty(xy[a][1])), (tx(xy[b][0]), ty(xy[b][1]))
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = x2 - x1, y2 - y1
        n = math.hypot(dx, dy)
        ox, oy = -dy / n, dx / n                      # off the road, to one side
        if abs(dy) < 1:                               # level: below it
            if oy < 0:
                ox, oy = -ox, -oy
        else:                                         # slanting: away from its upper end, so the
            top = x1 if y1 < y2 else x2               # two roads of a triangle keep their labels apart
            side = 1 if mx >= top else -1
            if ox * side < 0:
                ox, oy = -ox, -oy
        s = str(m)
        w = tw(s, 9, True) + 4
        k = 4 + abs(ox) * w / 2 + abs(oy) * 6           # clear of the road, however it slants
        lx, ly = mx + ox * k, my + oy * k
        f.add(f'<rect class="f" x="{fmt(round(lx - w / 2, 1))}" y="{fmt(round(ly - 6, 1))}" width="{fmt(round(w, 1))}" height="11" rx="2"/>')
        f.text(round(lx, 1), round(ly + 3.2, 1), s, "tm", 9, "middle", mono=True)


def junction(f, xy, j, state, label=None, now=False):
    """state: finished, waiting (in the queue or heap), seen (reached, in no container: unused
    here) or unseen."""
    x, y = tx(xy[j][0]), ty(xy[j][1])
    if now:
        f.circle(x, y, R + 5, "a")
    cls, tcls = {"finished": ("a fa", "f"), "waiting": ("a f", "ta"), "unseen": ("m f", "tm")}[state]
    f.circle(x, y, R, cls)
    f.text(x, y + 4, str(j), tcls, 11.5, "middle", 700 if state != "unseen" else None, mono=True)
    if label is not None:
        w = tw(label, 10, True) + 6
        lx, ly = x, y - R - 9 if xy[j][1] != 600 else y - R - 9
        if xy[j][1] == 0:
            ly = y + R + 13
        f.add(f'<rect class="f" x="{fmt(round(lx - w / 2, 1))}" y="{fmt(round(ly - 9, 1))}" width="{fmt(round(w, 1))}" height="12" rx="3"/>')
        f.text(lx, ly, label, "ta" if state != "unseen" else "tm", 10, "middle", 600, mono=True)


def tree_edge(f, xy, a, b, cls="a", width=None):
    w = f' stroke-width="{width}"' if width else ' stroke-width="2.5"'
    f.add(f'<line class="{cls}" x1="{fmt(round(tx(xy[a][0]), 1))}" y1="{fmt(round(ty(xy[a][1]), 1))}" '
          f'x2="{fmt(round(tx(xy[b][0]), 1))}" y2="{fmt(round(ty(xy[b][1]), 1))}"{w} stroke-linecap="round"/>')


def legend(f, y, waiting_label, way_label, value_label, sample):
    """Two rows under the figure: what the circles mean, then what the lines and labels mean."""
    x = 24
    for cls, label in (("a fa", "finished"), ("a f", waiting_label), ("m f", "not reached")):
        f.circle(x + 7, y - 4, 7, cls)
        f.text(x + 20, y, label, "tm", 11)
        x += 20 + tw(label, 11) + 22
    f.circle(x + 7, y - 4, 10, "a")
    f.circle(x + 7, y - 4, 5, "a fa")
    f.text(x + 22, y, "just finished", "tm", 11)
    y += 22
    x = 24
    f.add(f'<line class="a" x1="{x}" y1="{y - 4}" x2="{x + 22}" y2="{y - 4}" stroke-width="2.5" stroke-linecap="round"/>')
    f.text(x + 30, y, way_label, "tm", 11)
    x += 30 + tw(way_label, 11) + 22
    f.add(f'<line class="s" x1="{x}" y1="{y - 4}" x2="{x + 22}" y2="{y - 4}" stroke-width="4" stroke-linecap="round"/>')
    f.text(x + 30, y, "the route, at the end", "tm", 11)
    x += 30 + tw("the route, at the end", 11) + 22
    f.text(x, y, sample, "ta", 10, weight=600, mono=True)
    f.text(x + tw(sample, 10, True) + 8, y, value_label, "tm", 11)


def container_row(f, y, label, items, old_mark=True):
    """The queue or the heap, as the trace printed it: boxes J:D, front or top first; the
    label on a line of its own above them."""
    f.text(24, y, label, "tm", 11)
    x, y = 24, y + 4
    if not items:
        f.text(x, y + 20, "(empty)", "tm", 11, mono=True)
    for j, v, old in items:
        s = f"{j}:{v}"
        w = max(44, tw(s, 11.5, True) + 12)
        if old and old_mark:
            f.rect(x, y + 4, w, 24, "m fs", 5, dash=True)
            f.text(x + w / 2, y + 20, s, "tm", 11.5, "middle", mono=True)
            f.text(x + w / 2, y + 41, "old", "tm", 10, "middle")
        else:
            f.rect(x, y + 4, w, 24, "a f", 5)
            f.text(x + w / 2, y + 20, s, "ta", 11.5, "middle", 600, mono=True)
        x += w + 6


def prevs_from_trace(trace):
    """prev[] as the search had it after each line: a junction whose value in the container is
    new or changed got it from the junction just finished (only that one's roads were followed)."""
    prev, val, out = {}, {}, []
    for t in trace:
        if t["kind"] == "finish":
            if t["frm"] is not None:
                prev[t["j"]] = t["frm"]
            for j, v, old in t["items"]:
                if not old and val.get(j) != v:
                    if j != t["j"]:
                        prev[j] = t["j"]
                    val[j] = v
        out.append(dict(prev))
    return out


def walk(prev, to):
    p = [to]
    while p[-1] in prev:
        p.append(prev[p[-1]])
    return p[::-1]


def stepped_search(algo, title, key, waiting_label, box_label, unit, caption, way_label, value_label, sample,
                   box_y=304, height=414):
    """A stepped figure of one search on tiny.map from 3 to 8, from its DS_TRACE lines."""
    xy, roads, _ = load_map("tiny.map")
    out, err = route(f"--algo={algo}", "tools/route/tiny.map", "3", "8", trace=True)
    trace = parse_trace(err, algo)
    path, summary = path_of(out)
    prevs = prevs_from_trace(trace)
    f = Fig(key, title, height)
    draw_roads(f, xy, roads)
    f.text(tx(xy[3][0]), ty(xy[3][1]) + R + 28, "FROM", "tm", 9.5, "middle", 600)
    f.text(tx(xy[8][0]), ty(xy[8][1]) + R + 28, "TO", "tm", 9.5, "middle", 600)
    legend(f, height - 36, waiting_label, way_label, value_label, sample)
    finished, value = set(), {}
    for k, t in enumerate(trace):
        last = k == len(trace) - 1
        if t["kind"] == "finish":
            finished.add(t["j"])
            value[t["j"]] = t["d"] if algo != "astar" else t["sum"]
        waiting = {}
        for j, v, old in t["items"]:
            if not old and j not in finished:
                waiting[j] = v
        prev = prevs[k]
        with steps.step(f, caption(t, trace[k - 1] if k else None, last, summary)):
            for v, u in sorted(prev.items()):
                if v in finished or v in waiting:
                    tree_edge(f, xy, u, v)
            if last:
                for a, b in zip(path, path[1:]):
                    tree_edge(f, xy, a, b, "s", 4)
            for j in range(len(xy)):
                if j in finished:
                    lab = value[j]
                    junction(f, xy, j, "finished", unit(lab, j, t), now=j == t["j"])
                elif j in waiting:
                    junction(f, xy, j, "waiting", unit(waiting[j], j, t))
                else:
                    junction(f, xy, j, "unseen")
            container_row(f, box_y, box_label, t["items"])
    return f, trace


def new_items(t, before):
    had = {(j, v) for j, v, _ in (before["items"] if before else [])}
    return [(j, v) for j, v, old in t["items"] if not old and (j, v) not in had and j != t["j"]]


def bfs():
    def unit(v, j, t):
        return str(v)

    def caption(t, before, last, summary):
        d = t["d"]
        roads = "road" if d == 1 else "roads"
        frm = "the start" if t["frm"] is None else f"from {t['frm']}"
        head = f"Finish {t['j']} at {d} {roads} ({frm})."
        added = new_items(t, before)
        if last:
            return f"{head} It is TO, so the search stops: the route 3, 1, 8 is 2 roads and 1200 metres."
        if added:
            return f"{head} To the back of the queue: " + ", ".join(f"{j} at {v}" for j, v in added) + "."
        return f"{head} Its roads lead only to junctions reached already."

    f, trace = stepped_search("bfs", "Breadth-first search on tiny.map from 3 to 8, one frame per junction finished",
                              "f0802a", "in the queue", "queue, front first:", unit, caption,
                              "the road it was reached by", "roads from 3", "2")
    return f


def dijkstra():
    def unit(v, j, t):
        return f"{v}"

    def caption(t, before, last, summary):
        frm = "the start" if t["frm"] is None else f"from {t['frm']}"
        head = f"Finish {t['j']} at {t['d']} m ({frm})."
        old_before = {(j, v) for j, v, o in (before["items"] if before else []) if o}
        newly_old = [(j, v) for j, v, o in t["items"] if o and (j, v) not in old_before]
        added = new_items(t, before)
        bits = []
        if added:
            bits.append("Pushed: " + ", ".join(f"{j} at {v}" for j, v in added) + ".")
        if newly_old:
            j, v = newly_old[0]
            nv = next(x for jj, x, o in t["items"] if jj == j and not o)
            bits.append(f"{j} was at {v}: now {nv}, pushed again; the entry at {v} is out of date and stays.")
        if last:
            return f"{head} It is TO: the route along the main street is 1000 metres. An old entry is left in the heap."
        if not bits:
            return f"{head} Nothing new: its roads lead to junctions finished, or no nearer than they were."
        return head + " " + " ".join(bits)

    f, trace = stepped_search("dijkstra", "Dijkstra with a heap on tiny.map from 3 to 8, one frame per junction finished",
                              "f0803a", "on the heap", "heap's array, top first:", unit, caption,
                              "the best way in so far", "metres from 3", "430")
    return f


def astar():
    xy, _, _ = load_map("tiny.map")

    def unit(v, j, t):
        return f"{v}"

    def caption(t, before, last, summary):
        frm = "the start" if t["frm"] is None else f"from {t['frm']}"
        head = f"Finish {t['j']}: {t['d']} m so far + guess {t['guess']} = {t['sum']} ({frm})."
        added = new_items(t, before)
        if last:
            return f"{head} It is TO: 1000 metres, after finishing 6 junctions."
        if added:
            return head + " Pushed: " + ", ".join(f"{j} at {v}" for j, v in added) + "."
        return head + " Nothing new."

    f, trace = stepped_search("astar", "A* on tiny.map from 3 to 8: the heap is ordered by distance plus guess",
                              "f0804a", "on the heap", "heap's array, top first; key = metres so far + guess:", unit,
                              caption, "the best way in so far", "metres so far + guess", "1183", box_y=346, height=450)
    # every junction's guess, the straight line to 8 (the base, the same in every frame): whole
    # metres here; the program adds the exact value, so a key prints as 1183 for 600 + 583.1
    guesses = "  ".join(f"{j}:{round(math.hypot(x - xy[8][0], y - xy[8][1]))}" for j, (x, y) in enumerate(xy))
    f.out[0:0] = [f'<text class="tm" x="24" y="304" font-size="11">the guess at each junction, the straight line to 8:</text>',
                  f'<text class="t mono" x="24" y="320" font-size="10.5">{guesses}</text>']
    return f


# ------------------------------------------------------------------ 08.01: the adjacency lists

def lists0801():
    xy, roads, _ = load_map("tiny.map")
    n, m = len(xy), len(roads)
    first = [0] * (n + 1)
    for a, b, _ in roads:
        first[a + 1] += 1
        first[b + 1] += 1
    for j in range(n):
        first[j + 1] += first[j]
    nxt = first[:n]
    to, ln = [None] * (2 * m), [None] * (2 * m)
    for a, b, l in roads:
        to[nxt[a]], ln[nxt[a]] = b, l
        nxt[a] += 1
        to[nxt[b]], ln[nxt[b]] = a, l
        nxt[b] += 1
    # check against what bin/route says of the map
    out, _ = route("--info", "tools/route/tiny.map")
    assert out.startswith(f"junctions {n}, roads {m},"), out

    f = Fig("f0801a", "tiny.map as a graph, and its adjacency lists: first[], to[] and len[]", 452)
    pick = 3
    draw_roads(f, xy, roads)
    for k in range(first[pick], first[pick + 1]):
        tree_edge(f, xy, pick, to[k])
    for j in range(n):
        st = "finished" if j == pick else ("waiting" if j in to[first[pick]:first[pick + 1]] else "unseen")
        if st == "unseen":
            x, y = tx(xy[j][0]), ty(xy[j][1])
            f.circle(x, y, R, "s f")
            f.text(x, y + 4, str(j), "t", 11.5, "middle", 600, mono=True)
        else:
            junction(f, xy, j, st)
    f.text(24, 22, "tiny.map: 12 junctions, 21 roads, each road both ways; junction 3 and its 5 roads in colour", "tm", 11)

    # the arrays
    y0 = 302
    x0 = 82
    f.text(24, y0 + 15, "first[]", "t", 11, mono=True, weight=600)
    for j in range(n + 1):
        x = x0 + j * 40
        hot = j in (pick, pick + 1)
        f.rect(x, y0, 36, 22, "a af" if hot else "s f", 3)
        f.text(x + 18, y0 + 15, str(first[j]), "ta" if hot else "t", 11, "middle", 600 if hot else None, mono=True)
        f.text(x + 18, y0 - 5, str(j), "tm", 9, "middle", mono=True)
    y1 = y0 + 52
    f.text(24, y1 + 15, "to[]", "t", 11, mono=True, weight=600)
    f.text(24, y1 + 41, "len[]", "t", 11, mono=True, weight=600)
    # 42 arcs do not fit in one row of readable boxes; the first 21 hold junction 3's share
    per = 21
    cw = (640 - x0 - 16) / per
    for i, k in enumerate(range(0, per)):
        x = x0 + i * cw
        hot = first[pick] <= k < first[pick + 1]
        f.rect(x, y1, cw - 3, 22, "a af" if hot else "s f", 3)
        f.text(x + (cw - 3) / 2, y1 + 15, str(to[k]), "ta" if hot else "t", 10.5, "middle", 600 if hot else None, mono=True)
        f.rect(x, y1 + 26, cw - 3, 22, "a af" if hot else "s f", 3)
        f.text(x + (cw - 3) / 2, y1 + 41, str(ln[k]), "ta" if hot else "t", 9.5, "middle", None, mono=True)
        f.text(x + (cw - 3) / 2, y1 - 5, str(k), "tm", 9, "middle", mono=True)
    f.text(640 - 16, y1 + 92, f"arcs 21 to {2 * m - 1} go on in the same way: 2 x 21 roads = {2 * m} arcs", "tm", 10.5, "end")
    a0, a1 = first[pick], first[pick + 1]
    xa, xb = x0 + a0 * cw, x0 + a1 * cw - 3
    f.brace_h(xa, xb, y1 + 56, "a")
    f.text((xa + xb) / 2, y1 + 70, f"junction 3: arcs first[3] = {a0} to first[4] - 1 = {a1 - 1}", "ta", 10.5, "middle", 600)
    # the arrows from first[3] and first[4] down to where they point
    f.line(x0 + pick * 40 + 18, y0 + 25, xa + (cw - 3) / 2, y1 - 17, "a", arrow=True)
    f.line(x0 + (pick + 1) * 40 + 18, y0 + 25, x0 + a1 * cw + (cw - 3) / 2, y1 - 17, "m", arrow=True)
    return f


# ------------------------------------------------------------------ London, thinned



class View:
    """Where a box of the map (metres) lands in the figure: a panel at (px, py), w px wide."""

    def __init__(self, box, px, py, w, unit):
        self.x0, self.y0, self.x1, self.y1 = box
        self.px, self.py, self.w, self.unit = px, py, w, unit      # unit: metres a unit of the drawing
        self.s = w / ((self.x1 - self.x0) / unit)                   # figure px per unit
        self.h = (self.y1 - self.y0) / unit * self.s

    def u(self, x, y):
        """A map point, in whole units from the box's top left."""
        return round((x - self.x0) / self.unit), round((self.y1 - y) / self.unit)

    def inside(self, x, y):
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1

    def fig(self, x, y):
        ux, uy = self.u(x, y)
        return self.px + ux * self.s, self.py + uy * self.s

    def group(self, cls, width, d, opacity=None):
        op = f' stroke-opacity="{opacity}"' if opacity else ""
        return (f'<g transform="translate({fmt(round(self.px, 2))} {fmt(round(self.py, 2))}) scale({self.s:.5f})">'
                f'<path class="{cls}" d="{d}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" '
                f'vector-effect="non-scaling-stroke"{op}/></g>')


def chains(segs):
    """The segments [(p, q)] (points in units) joined into as few chains as a greedy walk finds;
    as one path's d, with relative moves."""
    adj = {}
    for i, (p, q) in enumerate(segs):
        adj.setdefault(p, []).append((i, q))
        adj.setdefault(q, []).append((i, p))
    used = [False] * len(segs)
    out = []
    pos = None
    # start chains at odd points first, so that fewer chains are needed
    starts = sorted(adj, key=lambda p: (len(adj[p]) % 2 == 0, p))
    for s in starts:
        while True:
            nxt = next(((i, q) for i, q in adj[s] if not used[i]), None)
            if nxt is None:
                break
            out.append(f"M{s[0]} {s[1]}" if pos is None else f"m{s[0] - pos[0]} {s[1] - pos[1]}")
            cur = s
            while nxt is not None:
                i, q = nxt
                used[i] = True
                out.append(f"l{q[0] - cur[0]} {q[1] - cur[1]}")
                cur = q
                nxt = next(((i, q) for i, q in adj[cur] if not used[i]), None)
            pos = cur
    d = "".join(out)
    return d.replace(" -", "-")


def clip(view, p, q):
    """The part of the straight line p-q (metres) inside the view's box, or None (Liang-Barsky)."""
    (x1, y1), (x2, y2) = p, q
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for pk, qk in ((-dx, x1 - view.x0), (dx, view.x1 - x1), (-dy, y1 - view.y0), (dy, view.y1 - y1)):
        if pk == 0:
            if qk < 0:
                return None
            continue
        t = qk / pk
        if pk < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return None
    return (x1 + t0 * dx, y1 + t0 * dy), (x1 + t1 * dx, y1 + t1 * dy)


def segments(view, xy, roads, keep=None):
    """The roads (with keep, those with an end in keep) cut to the view's box, as unit segments,
    each once; roads that shrink to a point are left out."""
    seen, segs = set(), []
    for a, b, _ in roads:
        if keep is not None and a not in keep and b not in keep:
            continue
        cut = clip(view, xy[a], xy[b])
        if cut is None:
            continue
        p, q = view.u(*cut[0]), view.u(*cut[1])
        if p == q:
            continue
        k = (min(p, q), max(p, q))
        if k in seen:
            continue
        seen.add(k)
        segs.append((p, q))
    return segs


def route_d(view, xy, path):
    pts = [view.u(*xy[j]) for j in path]
    out = [f"M{pts[0][0]} {pts[0][1]}"]
    cur = pts[0]
    for p in pts[1:]:
        if p != cur:
            out.append(f"l{p[0] - cur[0]} {p[1] - cur[1]}")
            cur = p
    return "".join(out).replace(" -", "-")


def finished_of(err, algo):
    return {int(m.group(1)) for m in re.finditer(r"^trace: " + re.escape(algo) + r": finish (\d+)", err, re.M)}


def frame(f, view, label=None):
    f.rect(view.px, view.py, view.w, view.h, "m", 0)
    if label:
        f.text(view.px, view.py - 8, label, "t", 12, weight=600)


def credit_line(f, credit, y, size=10.5):
    """The map's credit, as its licence asks: on two lines when it does not fit on one."""
    if tw(credit, size) <= 600:
        f.text(624, y, credit, "tm", size, "end")
        return
    cut = credit.index(", under ") + 1
    f.text(624, y - size - 3, credit[:cut], "tm", size, "end")
    f.text(624, y, credit[cut + 1:], "tm", size, "end")


def dot(f, x, y, cls):
    f.circle(round(x, 1), round(y, 1), 5, cls)


def london_routes():
    """08.02: the fewest junctions against the fewest metres, the centre pair."""
    xy, roads, credit = load_map("london.map")
    a, b = "4500,3500", "8000,5000"
    out_b, _ = route("--algo=bfs", "tools/route/london.map", a, b)
    out_d, _ = route("--algo=dijkstra", "tools/route/london.map", a, b)
    pb, sb = path_of(out_b)
    pd, sd = path_of(out_d)
    xs = [xy[j][0] for j in pb + pd]
    ys = [xy[j][1] for j in pb + pd]
    pad = 450
    box = (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
    view = View(box, 16, 52, 608, 8)
    h = 52 + view.h + 86
    f = Fig("f0802b", "Central London, the same two points: the route with the fewest junctions, and the shortest", round(h))
    f.text(16, 20, f"bfs, the fewest junctions: {sb.split(': ', 1)[1]}", "ta", 12, weight=600)
    f.text(16, 38, f"the shortest (Dijkstra, 08.03): {sd.split(': ', 1)[1]}", "t", 12, weight=600)
    f.add(view.group("m", 0.8, chains(segments(view, xy, roads))))
    f.add(view.group("s", 3, route_d(view, xy, pd)))
    f.add(view.group("a", 3, route_d(view, xy, pb), opacity=None))
    frame(f, view)
    x, y = view.fig(*xy[pb[0]])
    dot(f, x, y, "s fa")
    f.text(x - 10, y + 4, "FROM", "t", 10.5, "end", 700)
    x, y = view.fig(*xy[pb[-1]])
    dot(f, x, y, "s fa")
    f.text(x + 10, y + 4, "TO", "t", 10.5, "start", 700)
    km = 1000 / view.unit * view.s
    yb = 52 + view.h + 22
    f.line(16, yb, 16 + km, yb, "s")
    f.line(16, yb - 4, 16, yb + 4, "s")
    f.line(16 + km, yb - 4, 16 + km, yb + 4, "s")
    f.text(16 + km + 8, yb + 4, "1 km", "tm", 10.5)
    credit_line(f, credit, h - 10, 13)
    return f, (sb, sd)


def london_disc_band():
    """08.04: what Dijkstra finishes against what A* finishes, the centre pair."""
    xy, roads, credit = load_map("london.map")
    a, b = "4500,3500", "8000,5000"
    panels = []
    for algo in ("dijkstra", "astar"):
        out, err = route(f"--algo={algo}", "tools/route/london.map", a, b, trace=True)
        panels.append((algo, path_of(out), finished_of(err, algo)))
    fin = panels[0][2] | panels[1][2]
    xs = [xy[j][0] for j in fin]
    ys = [xy[j][1] for j in fin]
    pad = 200
    box = (max(0, min(xs) - pad), max(0, min(ys) - pad), max(xs) + pad, max(ys) + pad)
    w = 296
    views = [View(box, 16, 44, w, 26), View(box, 16 + w + 16, 44, w, 26)]
    h = 44 + views[0].h + 84
    f = Fig("f0804b", "Central London, the same route found twice: the junctions Dijkstra finished, and those A* finished",
            round(h))
    for view, (algo, (path, summary), done) in zip(views, panels):
        name = "Dijkstra" if algo == "dijkstra" else "A*"
        f.text(view.px, 20, f"{name}: {len(done)} junctions finished", "ta", 12, weight=600)
        f.text(view.px, 36, summary.split(": ", 1)[1], "tm", 11)
        f.add(view.group("m", 0.6, chains(segments(view, xy, roads))))
        f.add(view.group("a", 1.1, chains(segments(view, xy, roads, keep=done))))
        f.add(view.group("s", 2.5, route_d(view, xy, path)))
        frame(f, view)
        x, y = view.fig(*xy[path[0]])
        dot(f, x, y, "s fa")
        x, y = view.fig(*xy[path[-1]])
        dot(f, x, y, "s fa")
    f.text(16, 44 + views[0].h + 20, "in colour: the roads at every junction the search finished; the thick line: the route",
           "tm", 11)
    credit_line(f, credit, h - 8, 13)
    return f, [(p[0], len(p[2])) for p in panels]


# ------------------------------------------------------------------ main

def save(name, f, stepped=False):
    p = figlib.write(MOD, name, f)
    text = open(p).read()
    size = len(text.encode())
    n = steps.check(text) if stepped else 0
    sys.path.insert(0, ROOT)
    from harness.web.art import sanitize
    clean = sanitize(text, "x")
    if not clean:
        raise SystemExit(f"{p}: rejected by the sanitizer")
    if clean.count("<") - clean.count("</") != text.count("<") - text.count("</"):
        raise SystemExit(f"{p}: the sanitizer dropped an element")
    if size > 200 * 1024:
        raise SystemExit(f"{p}: {size} bytes, over the 200 KB a figure may be")
    print(f"{os.path.relpath(p, ROOT)}: {size} bytes" + (f", {n} steps" if stepped else ""))


def main():
    build()
    save("08.01-lists", lists0801())
    save("08.02-bfs", bfs(), stepped=True)
    f, info = london_routes()
    save("08.02-london", f)
    save("08.03-heap", dijkstra(), stepped=True)
    save("08.04-astar", astar(), stepped=True)
    f, info = london_disc_band()
    save("08.04-london", f)
    print("finished:", info)


if __name__ == "__main__":
    main()
