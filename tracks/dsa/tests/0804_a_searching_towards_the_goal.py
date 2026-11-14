"""08.04 A*: searching towards the goal

route --algo=astar finds routes as long as Dijkstra's and the plain Python reference's, for a
table of start and end points on the London map, finishing far fewer junctions: exactly those
whose distance plus the straight line to the end is less than the route (and perhaps some equal),
never one beyond. That holds because no road on the map is shorter than the straight line between
its ends, which the test checks of every road, and so the straight line to the end never
overestimates. On the tiny map A* finishes the six junctions of the main street where Dijkstra
finishes all twelve. A* is the default.
"""

import math
import os


def test(t):
    T = t.track
    fx = T.fixtures("route")
    mp = fx.load(os.path.join(t.root, fx.LONDON))

    # the guess can never overestimate: no road is shorter than the straight line between its ends
    for path in (fx.LONDON, fx.TINY):
        m = fx.load(os.path.join(t.root, path))
        short = [(a, b, metres) for a, b, metres in m.roads if math.dist(m.xy[a], m.xy[b]) > metres]
        t.check(not short, f"{path}: roads shorter than the straight line: {short[:5]}")

    table = fx.pairs(mp, 10, 4) + [(fx.nearest(mp, a), fx.nearest(mp, b)) for a, b in fx.PLACES]
    total = {"astar": 0, "dijkstra": 0}
    for s, to in table:
        metres, _ = fx.ref_dijkstra(mp, s, to)
        _, dist = fx.ref_dijkstra(mp, s, None)
        got = {}
        for algo in ("dijkstra", "astar", None):
            r, st, res = fx.route(t, fx.LONDON, s, to, algo=algo)
            if metres is None:
                t.check(r is None, f"{algo} {s} {to}: no road joins them, route found one:\n{res}")
            else:
                t.check(r is not None and r.metres == metres,
                        f"{algo} {s} {to}: the shortest is {metres} metres, route found {r and r.metres}")
            got[algo] = st["route"]
        t.check(got[None] == got["astar"], f"{s} {to}: A* is the default: {got[None]} {got['astar']}")
        if metres is None:
            continue
        x, y = mp.xy[to]
        f = [d + math.hypot(mp.xy[j][0] - x, mp.xy[j][1] - y) for j, d in dist.items()]
        below = sum(1 for v in f if v < metres - 1e-6)
        upto = sum(1 for v in f if v <= metres + 1e-6)
        t.check(below < got["astar"]["finished"] <= upto,
                f"astar {s} {to}: finishes the {below} junctions below {metres} metres, none above: {got['astar']}")
        t.check(got["astar"]["finished"] <= got["dijkstra"]["finished"], f"{s} {to}: {got}")
        for algo in total:
            total[algo] += got[algo]["finished"]
    t.check(2 * total["astar"] < total["dijkstra"], f"A* finishes less than half Dijkstra's junctions: {total}")

    # across the map, west to east
    s, to = fx.nearest(mp, fx.PLACES[0][0]), fx.nearest(mp, fx.PLACES[0][1])
    _, a, _ = fx.route(t, fx.LONDON, s, to, algo="astar")
    _, d, _ = fx.route(t, fx.LONDON, s, to, algo="dijkstra")
    t.check(2 * a["route"]["finished"] < d["route"]["finished"], f"west to east: {a} against {d}")

    # the tiny map: the six junctions of the main street, not all twelve
    got, st, _ = fx.route(t, fx.TINY, 3, 8, algo="astar")
    t.check(got.junctions == [3, 4, 5, 6, 7, 8] and st["route"]["finished"] == 6, f"astar on the tiny map: {st}")
    r = T.run(t, "route", ["--algo=astar", fx.TINY, "3", "8"], env={"DS_TRACE": "1"})
    lines = r.err.splitlines()
    t.check(len(lines) == 6 and lines[0] == "trace: astar: finish 3 at 0, guess 1000, sum 1000 (start); "
            "heap: 4:1000 1:1183 2:1600 0:1764 9:1607", f"astar's trace:\n{r.err}")
    t.check(lines[-1].startswith("trace: astar: finish 8 at 1000, guess 0, sum 1000 (from 7); heap: "), f"{lines[-1]!r}")
