"""08.02 Breadth-first search: the fewest junctions

route --algo=bfs finds a route with as few roads as a plain Python breadth-first search finds, for
a table of start and end points on the London map; the route is real (each junction joined to the
next, its metres adding up); it finishes every junction fewer roads away than the end and none
further; and its routes are often longer in metres than the shortest, on the tiny map by design
and on London on most of the table. Two junctions no road joins have no route (exit 1); a junction
to itself is a route of one. DS_TRACE prints one line for each junction finished, with the queue.
--svg draws the route.
"""

import os
import re
import xml.etree.ElementTree as ET


def test(t):
    T = t.track
    fx = T.fixtures("route")
    mp = fx.load(os.path.join(t.root, fx.LONDON))

    longer = 0
    table = fx.pairs(mp, 16, 2) + [(fx.nearest(mp, a), fx.nearest(mp, b)) for a, b in fx.PLACES]
    for s, to in table:
        hops, all_hops = fx.ref_bfs(mp, s, to)
        got, st, r = fx.route(t, fx.LONDON, s, to, algo="bfs")
        if hops is None:
            t.check(got is None, f"bfs {s} {to}: no road joins them, route found one:\n{r}")
            continue
        t.check(got is not None and len(got.junctions) - 1 == hops,
                f"bfs {s} {to}: {hops} roads at the fewest, route took {got and len(got.junctions) - 1}")
        s_ = st["route"]
        nearer = sum(1 for h in all_hops.values() if h < hops)
        upto = sum(1 for h in all_hops.values() if h <= hops)
        t.check(nearer < s_["finished"] <= upto,
                f"bfs {s} {to}: finishes all {nearer} junctions nearer than {hops} roads, none further: {s_}")
        t.check(s_["reached"] <= mp.n and s_["scanned"] == 0 and s_["stale"] == 0, f"bfs {s} {to}: {s_}")
        metres, _ = fx.ref_dijkstra(mp, s, to)
        t.check(got.metres >= metres, f"bfs {s} {to}: {got.metres} metres, shorter than the shortest {metres}?")
        longer += got.metres > metres
    t.check(longer >= len(table) // 2,
            f"the fewest junctions are longer in metres than the shortest route on {longer} of {len(table)} only")

    # the tiny map: 3 roads round the ring, 1200 metres; the main street is 1000 in 5 roads
    got, st, _ = fx.route(t, fx.TINY, 3, 8, algo="bfs")
    t.check(got.junctions == [3, 1, 8] and got.metres == 1200, f"bfs on the tiny map: {got.junctions}")
    r = T.run(t, "route", ["--algo=bfs", fx.TINY, "3", "8"], env={"DS_TRACE": "1"})
    lines = r.err.splitlines()
    t.check(len(lines) == 8 and all(l.startswith("trace: bfs: finish ") for l in lines), f"one line a junction:\n{r.err}")
    t.check(lines[0] == "trace: bfs: finish 3 at 0 (start); queue: 0:1 1:1 2:1 4:1 9:1", f"{lines[0]!r}")
    t.check(lines[-1] == "trace: bfs: finish 8 at 2 (from 1); queue: 5:2 10:2 7:3 11:3", f"{lines[-1]!r}")

    # no road between them; a junction to itself; a point for a junction
    hops, all_hops = fx.ref_bfs(mp, 0, 0)
    other = next(j for j in range(mp.n) if j not in all_hops)
    got, st, r = fx.route(t, fx.LONDON, 0, other, algo="bfs")
    t.check(got is None and r.rc == 1, f"bfs 0 {other}, two pieces:\n{r}")
    got, _, _ = fx.route(t, fx.LONDON, 77, 77, algo="bfs")
    t.check(got.junctions == [77] and got.metres == 0, f"bfs 77 77: {got.junctions}")
    r = T.run(t, "route", ["--algo=bfs", fx.TINY, "390,310", "1500,250"])
    t.check(r.out.startswith("from 3 to 8: "), f"the nearest junctions to two points:\n{r.out}")
    for a, b in fx.PLACES:
        r = T.run(t, "route", ["--algo=bfs", fx.LONDON, a, b], check=False)
        want = f"from {fx.nearest(mp, a)} to {fx.nearest(mp, b)}: "
        t.check(r.out.startswith(want), f"route {a} {b}: the nearest junctions are {want}\n{r.out[:200]}")

    # the picture
    svg = os.path.join(t.tmp, "bfs.svg")
    T.run(t, "route", ["--algo=bfs", f"--svg={svg}", fx.TINY, "3", "8"])
    root = ET.parse(svg).getroot()
    paths = [e.get("d") for e in root.iter() if e.tag.endswith("path")]
    # in metres here (a small map): 3 to 1 is 500 east and 300 south, 1 to 8 500 east, 300 north
    t.check(len(paths) == 3 and re.match(r"^M\d+ \d+l500 300l500 -300$", paths[2]), f"the route drawn: {paths}")
    t.check(len([e for e in root.iter() if e.tag.endswith("circle")]) == 12 + 2, "each junction, and the two ends")

    for args, msg in (([fx.TINY, "3", "12"], "no junction 12: the map's are 0 to 11"),
                      ([fx.TINY, "3", "x,y"], "'x,y' is not a junction"),
                      ([fx.TINY, "3"], "usage: route")):
        r = T.run(t, "route", ["--algo=bfs"] + args, check=False)
        t.check(r.rc == 2 and msg in r.err, f"route {' '.join(args)}:\n{r}")
