"""route: the shortest way between two junctions of a road map (module 08). T is track.py.

There is no system tool to hold route to, so every search is held to a plain reference here,
written the straightforward way in Python on the same map file.

    LONDON, TINY        the maps' paths under the project root
    load(path)          a map file: Map with .xy [(x, y)], .roads [(a, b, metres)], .adj
                        [[(junction, metres), ...]] (both ways), .n, .m
    ref_dijkstra(mp, s, t)
                        the shortest route's metres, or None; and {junction: metres} for every
                        junction it finished, which is every one nearer than t (heapq, no stops)
    ref_bfs(mp, s, t)   the fewest roads from s to t, or None; and {junction: roads} for all
    ref_pieces(mp)      the sizes of the connected pieces, the largest first
    parse(out)          route's output: Route with .frm .to .metres .junctions (a list) .steps
                        [(metres so far, junction)], or None for "no route"
    check_route(mp, r)  fail unless r is a real route on mp: each junction joined to the next
                        by a road, the metres those roads add up to, and the sum line right
    route(t, mp_path, s, t2, algo=None, env=None)
                        bin/route [--algo=algo] path s t2 with DS_STATS=1: (Route or None, stats)
    pairs(mp, k, seed)  k (from, to) pairs of junctions, the same every run
    nearest(mp, "X,Y")  the junction nearest a point; PLACES, points on the London map
"""

import heapq
import os
import random
import re

from harness.core import Fail

PROGRAMS = {"route": "08.01"}
FILES_FROM = {
    "tools/route/tool.mk": "08.01",
    "lib/roadgraph.h": "08.01",
    "tools/route/london.map": "08.01",
    "tools/route/tiny.map": "08.01",
    "tools/route/gen.py": "08.01",
    "tools/route/NOTICE.txt": "08.01",
}
HIDDEN = ["tools/route/NOTES.md"]
UPSTREAM = [
    {"name": "OpenStreetMap",
     "url": "https://www.openstreetmap.org/copyright",
     "licence": "Open Database License (ODbL) 1.0",
     "copyright": "OpenStreetMap contributors",
     "owes": "No code. The road map route searches, tools/route/london.map, is made from "
             "OpenStreetMap data and is under the Open Database License, not MIT; "
             "tools/route/NOTICE.txt says where it came from and how it was made.",
     "also": [("The Open Database License 1.0", "https://opendatacommons.org/licenses/odbl/1-0/")],
     "chip": "map data from OpenStreetMap",
     "derived": False},
]

LONDON = "tools/route/london.map"
TINY = "tools/route/tiny.map"


class Map:
    def __init__(self, xy, roads, credit):
        self.xy, self.roads, self.credit = xy, roads, credit
        self.n, self.m = len(xy), len(roads)
        self.adj = [[] for _ in xy]
        for a, b, metres in roads:
            self.adj[a].append((b, metres))
            self.adj[b].append((a, metres))


_maps = {}


def load(path):
    """A map file, read the plain way (and kept: the tests read London many times)."""
    key = (os.path.abspath(path), os.path.getmtime(path))
    if key in _maps:
        return _maps[key]
    with open(path) as f:
        lines = [l.rstrip("\n") for l in f if l.strip() and not l.startswith("#")]
    credit = None
    if lines[0].startswith("credit "):
        credit = lines.pop(0)[7:]
    n = int(lines[0].split()[1])
    xy = [tuple(int(v) for v in l.split()) for l in lines[1:1 + n]]
    m = int(lines[1 + n].split()[1])
    roads = [tuple(int(v) for v in l.split()) for l in lines[2 + n:2 + n + m]]
    if len(roads) != m:
        raise Fail(f"{path}: {len(roads)} roads, not {m}")
    _maps[key] = Map(xy, roads, credit)
    return _maps[key]


def ref_dijkstra(mp, s, t):
    """Dijkstra in the plainest Python: the metres from s to t (None if no road joins them), and
    the metres of every junction finished on the way (those nearer than t, and t)."""
    best = {s: 0}
    done = {}
    queue = [(0, s)]
    while queue:
        d, u = heapq.heappop(queue)
        if u in done:
            continue
        done[u] = d
        if u == t:
            return d, done
        for v, metres in mp.adj[u]:
            if v not in done and (v not in best or d + metres < best[v]):
                best[v] = d + metres
                heapq.heappush(queue, (d + metres, v))
    return None, done


def ref_bfs(mp, s, t):
    """The fewest roads from s to t (None if none), and the roads to every junction s reaches."""
    hops = {s: 0}
    level = [s]
    while level:
        nxt = []
        for u in level:
            for v, _ in mp.adj[u]:
                if v not in hops:
                    hops[v] = hops[u] + 1
                    nxt.append(v)
        level = nxt
    return hops.get(t), hops


def ref_pieces(mp):
    seen = [False] * mp.n
    sizes = []
    for s in range(mp.n):
        if seen[s]:
            continue
        seen[s] = True
        todo, size = [s], 0
        while todo:
            u = todo.pop()
            size += 1
            for v, _ in mp.adj[u]:
                if not seen[v]:
                    seen[v] = True
                    todo.append(v)
        sizes.append(size)
    return sorted(sizes, reverse=True)


class Route:
    pass


HEAD = re.compile(r"^from (\d+) to (\d+): (\d+) metres, (\d+) junctions?$")
NONE = re.compile(r"^from (\d+) to (\d+): no route: no road joins them$")


def parse(out):
    lines = out.splitlines()
    if not lines:
        raise Fail("route printed nothing")
    if NONE.match(lines[0]) and len(lines) == 1:
        return None
    m = HEAD.match(lines[0])
    if not m or lines[1].split() != ["metres", "junction", "x", "y"]:
        raise Fail(f"not a route:\n{out[:500]}")
    r = Route()
    r.frm, r.to, r.metres, count = (int(g) for g in m.groups())
    r.steps = []
    r.where = []
    for line in lines[2:]:
        so_far, j, x, y = (int(v) for v in line.split())
        r.steps.append((so_far, j))
        r.where.append((x, y))
    r.junctions = [j for _, j in r.steps]
    if len(r.junctions) != count:
        raise Fail(f"the route says {count} junctions and lists {len(r.junctions)}:\n{out[:500]}")
    return r


def check_route(mp, r):
    """Fail unless r is a route on mp: from r.frm to r.to, each junction joined to the next by a
    road, the metres so far adding up those roads (the shortest road, where two join the same
    junctions), the junctions where the map has them."""
    js = r.junctions
    if js[0] != r.frm or js[-1] != r.to:
        raise Fail(f"the route runs from {js[0]} to {js[-1]}, not {r.frm} to {r.to}")
    so_far = 0
    for k, j in enumerate(js):
        if r.where[k] != mp.xy[j]:
            raise Fail(f"junction {j} is at {mp.xy[j]}, the route says {r.where[k]}")
        if k:
            lens = [metres for v, metres in mp.adj[js[k - 1]] if v == j]
            if not lens:
                raise Fail(f"no road joins junctions {js[k - 1]} and {j}, which the route takes")
            so_far += min(lens)
        if r.steps[k][0] != so_far:
            raise Fail(f"at junction {j} the route says {r.steps[k][0]} metres, its roads add up to {so_far}")
    if so_far != r.metres:
        raise Fail(f"the route says {r.metres} metres, its roads add up to {so_far}")
    if len(set(js)) != len(js):
        raise Fail(f"the route goes through a junction twice: {js}")


def route(t, path, s, to, algo=None, env=None, check=True):
    """bin/route [--algo=algo] path s to, with DS_STATS=1: (Route or None, stats, Result)."""
    args = ([f"--algo={algo}"] if algo else []) + [path, str(s), str(to)]
    r = T.run(t, "route", args, env=dict({"DS_STATS": "1"}, **(env or {})), check=False)
    if r.rc not in (0, 1) or (r.rc == 1) != r.out.startswith(f"from {s} to {to}: no route"):
        raise Fail(f"bin/route {' '.join(args)}:\n{r}")
    got = parse(r.out)
    if got is not None and check:
        check_route(load(os.path.join(T._root(t), path) if not os.path.isabs(path) else path), got)
    return got, T.stats(r.err), r


def nearest(mp, point):
    """The junction nearest the point "X,Y" (the first of them, on a tie)."""
    x, y = (int(v) for v in point.split(","))
    return min(range(mp.n), key=lambda j: ((mp.xy[j][0] - x) ** 2 + (mp.xy[j][1] - y) ** 2, j))


def pairs(mp, k, seed):
    """k pairs of junctions, picked at random but the same every run; most far apart."""
    rng = random.Random(seed)
    return [(rng.randrange(mp.n), rng.randrange(mp.n)) for _ in range(k)]


# Hand-picked on the London map, by where they are (route takes X,Y and finds the nearest
# junction): west to east across the whole map, south to north over the Thames, short ones,
# and a corner to a corner.
PLACES = [("300,3500", "12000,4000"), ("6000,200", "6000,7500"), ("300,300", "12200,7500"),
          ("3000,6000", "9000,1000"), ("6200,3900", "6400,4100"), ("8000,4000", "8000,4600")]


# ---------------------------------------------------------------- check-timeline

TINY_INFO = ("junctions 12, roads 21, 7.7 km of road\n"
             "       7 junctions with 3 roads\n"
             "       4 junctions with 4 roads\n"
             "       1 junction  with 5 roads\n"
             "pieces 1: junctions in each, the largest first: 12\n")
ROUTE_HEAD = "  metres  junction       x       y\n"
BFS_ROUTE = ("from 3 to 8: 1200 metres, 3 junctions\n" + ROUTE_HEAD +
             "       0         3     400     300\n"
             "     600         1     900       0\n"
             "    1200         8    1400     300\n")
SHORTEST = ("from 3 to 8: 1000 metres, 6 junctions\n" + ROUTE_HEAD +
            "".join(f"{200 * k:8d} {3 + k:9d} {400 + 200 * k:7d} {300:7d}\n" for k in range(6)))


def timeline_steps(k):
    if k < (8, 1):
        return []
    steps = [T.sh_step(f"bin/route --info {TINY}", TINY_INFO)]
    if k < (8, 2):
        steps.append(T.sh_step(f"bin/route {TINY} 3 8", "route: no search to find a route with yet: try --info\n", 2))
        return steps
    steps.append(T.sh_step(f"bin/route {TINY} 3 8", BFS_ROUTE if k < (8, 3) else SHORTEST))
    if k < (8, 3):
        steps.append(T.sh_step(f"bin/route --algo=dijkstra {TINY} 3 8", "route: unknown option '--algo=dijkstra'\n", 2))
        return steps
    steps.append(T.sh_step(f"bin/route --algo=bfs {TINY} 3 8", BFS_ROUTE))
    steps.append(T.sh_step(f"bin/route --algo=dijkstra-scan {TINY} 3 8", SHORTEST))
    if k < (8, 4):
        steps.append(T.sh_step(f"bin/route --algo=astar {TINY} 3 8",
                               "route: no --algo 'astar' (have: bfs, dijkstra-scan, dijkstra)\n", 2))
    else:
        steps.append(T.sh_step(f"bin/route --algo=dijkstra {TINY} 3 8", SHORTEST))
    return steps


def timeline_after(root, k):
    if k < (8, 1):
        return None
    mp = load(os.path.join(root, LONDON))
    r = T.run(root, "route", ["--info", LONDON])
    sizes = ref_pieces(mp)
    if f"pieces {len(sizes)}: junctions in each, the largest first: {sizes[0]}," not in r.out:
        raise Fail(f"bin/route --info {LONDON}: not the map's {len(sizes)} pieces:\n{r.out}")
    if k < (8, 2):
        return f"route: the London map, {mp.n} junctions in {len(sizes)} pieces"
    for s, to in pairs(mp, 4, 8):
        want, _ = ref_dijkstra(mp, s, to) if k >= (8, 3) else ref_bfs(mp, s, to)
        got, _, _ = route(root, LONDON, s, to)
        have = None if got is None else (got.metres if k >= (8, 3) else len(got.junctions) - 1)
        if have != want:
            raise Fail(f"bin/route {LONDON} {s} {to}: {have}, the reference says {want}")
    return "route: the London map, four routes as the reference finds them"
