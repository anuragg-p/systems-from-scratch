"""08.03 Dijkstra, with a heap

route --algo=dijkstra-scan and --algo=dijkstra find routes exactly as long as a plain Python
Dijkstra finds, for a table of start and end points on the London map, and real ones. Each
finishes every junction nearer than the end and none further. The two pick the same junction at
every step, so they finish, reach and relax the same; but the scan looks at every junction for
each one it finishes (n times the finished), and the heap makes a hundred times fewer comparisons
than that on a route across the map. The heap has no decrease-key: a junction given a shorter
distance is pushed again, and its old entry is thrown away when it comes off (stale): pops are the
finished plus the stale. DS_TRACE shows each junction finished with the heap, old entries marked.
"""

import os


def test(t):
    T = t.track
    fx = T.fixtures("route")
    mp = fx.load(os.path.join(t.root, fx.LONDON))

    table = fx.pairs(mp, 10, 3) + [(fx.nearest(mp, a), fx.nearest(mp, b)) for a, b in fx.PLACES]
    stale = 0
    for s, to in table:
        metres, _ = fx.ref_dijkstra(mp, s, to)
        _, dist = fx.ref_dijkstra(mp, s, None)
        got = {}
        for algo in ("dijkstra-scan", "dijkstra"):
            r, st, res = fx.route(t, fx.LONDON, s, to, algo=algo)
            if metres is None:
                t.check(r is None, f"{algo} {s} {to}: no road joins them, route found one:\n{res}")
            else:
                t.check(r is not None and r.metres == metres,
                        f"{algo} {s} {to}: the shortest is {metres} metres, route found {r and r.metres}")
                nearer = sum(1 for d in dist.values() if d < metres)
                upto = sum(1 for d in dist.values() if d <= metres)
                f = st["route"]["finished"]
                t.check(nearer < f <= upto, f"{algo} {s} {to}: finishes the {nearer} nearer, none further: {st}")
            got[algo] = st
        sc, hp = got["dijkstra-scan"], got["dijkstra"]
        for k in ("finished", "reached", "relaxed"):
            t.check(sc["route"][k] == hp["route"][k], f"{s} {to}: the scan and the heap pick alike: {sc} {hp}")
        if metres is not None:
            t.check(sc["route"]["scanned"] == mp.n * sc["route"]["finished"],
                    f"{s} {to}: the scan looks at all {mp.n} junctions for each it finishes: {sc}")
        t.check(hp["route"]["scanned"] == 0 and "heap" not in sc, f"{s} {to}: {hp}")
        h = hp["heap"]
        t.check(h["pops"] == hp["route"]["finished"] + hp["route"]["stale"] and h["pushes"] >= h["pops"],
                f"{s} {to}: each pop finishes a junction or is stale: {hp}")
        stale += hp["route"]["stale"]
    t.check(stale > 0, "on London some junctions are given a shorter distance after they were pushed")

    # across the map: the heap's comparisons against the scan's junctions looked at
    s, to = fx.nearest(mp, fx.PLACES[0][0]), fx.nearest(mp, fx.PLACES[0][1])
    _, sc, _ = fx.route(t, fx.LONDON, s, to, algo="dijkstra-scan")
    _, hp, _ = fx.route(t, fx.LONDON, s, to, algo="dijkstra")
    t.check(hp["heap"]["comparisons"] * 100 < sc["route"]["scanned"],
            f"west to east: {hp['heap']['comparisons']} comparisons against {sc['route']['scanned']} looked at")

    # the tiny map: the main street, 1000 metres; every junction finished to know it
    for algo in ("dijkstra-scan", "dijkstra"):
        got, st, _ = fx.route(t, fx.TINY, 3, 8, algo=algo)
        t.check(got.junctions == [3, 4, 5, 6, 7, 8] and got.metres == 1000, f"{algo} on the tiny map: {got.junctions}")
        t.check(st["route"]["finished"] == 12, f"{algo} 3 8 finishes all 12: {st}")
    r = T.run(t, "route", ["--algo=dijkstra-scan", fx.TINY, "3", "8"], env={"DS_TRACE": "1"})
    lines = r.err.splitlines()
    t.check(len(lines) == 12 and lines[0] == "trace: dijkstra-scan: finish 3 at 0 (start); reached: 0:430 1:600 "
            "2:300 4:200 9:370" and lines[-1] == "trace: dijkstra-scan: finish 8 at 1000 (from 7); reached:",
            f"dijkstra-scan's trace:\n{r.err}")
    r = T.run(t, "route", ["--algo=dijkstra", fx.TINY, "0", "8"], env={"DS_TRACE": "1"})
    lines = r.err.splitlines()
    t.check(len(lines) == 14 and lines[0] == "trace: dijkstra: finish 0 at 0 (start); heap: 2:300 1:800 3:430",
            f"dijkstra's trace:\n{r.err}")
    t.check("trace: dijkstra: skip 6 at 1120, finished at 1030 already; heap: 10:1120(old) 7:1230 11:1350 8:1400"
            in lines, f"the old entry for 6 thrown away:\n{r.err}")
    t.check(lines[-1] == "trace: dijkstra: finish 8 at 1400 (from 1); heap:", f"{lines[-1]!r}")
